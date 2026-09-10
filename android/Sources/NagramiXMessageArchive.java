package com.mr_efes.nagramix;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.MessageObject;
import org.telegram.messenger.MessagesController;
import org.telegram.tgnet.NativeByteBuffer;
import org.telegram.tgnet.TLRPC;

import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.Consumer;

/** Account-scoped, display-only snapshots for observed edits and deletions. */
public final class NagramiXMessageArchive {
    private static final NagramiXMessageArchive[] INSTANCES = new NagramiXMessageArchive[4];

    public static NagramiXMessageArchive getInstance(int account) {
        synchronized (INSTANCES) {
            if (INSTANCES[account] == null) {
                INSTANCES[account] = new NagramiXMessageArchive(account);
            }
            return INSTANCES[account];
        }
    }

    private final int account;
    private final ArchiveDatabase database;
    private final ExecutorService queue;

    private NagramiXMessageArchive(int account) {
        this.account = account;
        this.database = new ArchiveDatabase(ApplicationLoader.applicationContext, account);
        this.queue = Executors.newSingleThreadExecutor(r -> {
            Thread thread = new Thread(r, "NagramiXArchive-" + account);
            thread.setPriority(Thread.MIN_PRIORITY);
            return thread;
        });
    }

    public void capture(ArrayList<TLRPC.Message> messages) {
        if (messages == null || messages.isEmpty()) return;
        final boolean deletedEnabled = NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext)
                .getBoolean(NagramiXSettings.SHOW_DELETED_MESSAGES, false);
        final boolean editsEnabled = NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext)
                .getBoolean(NagramiXSettings.EDIT_HISTORY, false);
        if (!deletedEnabled && !editsEnabled) return;
        ArrayList<TLRPC.Message> snapshots = new ArrayList<>(messages);
        queue.execute(() -> {
            SQLiteDatabase db = database.getWritableDatabase();
            db.beginTransaction();
            try {
                for (TLRPC.Message message : snapshots) {
                    if (!isEligible(message)) continue;
                    long dialogId = MessageObject.getDialogId(message);
                    byte[] value = serialize(message);
                    if (value == null) continue;
                    byte[] previous = currentValue(db, dialogId, message.id);
                    if (previous != null && editsEnabled && !Arrays.equals(previous, value)) {
                        ContentValues revision = new ContentValues();
                        revision.put("dialog_id", dialogId);
                        revision.put("message_id", message.id);
                        revision.put("observed_at", System.currentTimeMillis() / 1000L);
                        revision.put("data", previous);
                        db.insert("revisions", null, revision);
                    }
                    ContentValues record = new ContentValues();
                    record.put("dialog_id", dialogId);
                    record.put("message_id", message.id);
                    record.put("date", message.date);
                    record.put("data", value);
                    db.insertWithOnConflict("messages", null, record, SQLiteDatabase.CONFLICT_REPLACE);
                }
                db.setTransactionSuccessful();
            } finally {
                db.endTransaction();
            }
        });
    }

    public void markDeleted(long dialogId, ArrayList<Integer> messageIds) {
        if (messageIds == null || messageIds.isEmpty()) return;
        if (!NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext)
                .getBoolean(NagramiXSettings.SHOW_DELETED_MESSAGES, false)) return;
        final ArrayList<Integer> ids = new ArrayList<>(messageIds);
        queue.execute(() -> {
            SQLiteDatabase db = database.getWritableDatabase();
            ContentValues values = new ContentValues();
            values.put("deleted_at", System.currentTimeMillis() / 1000L);
            for (Integer id : ids) {
                if (dialogId == 0) {
                    db.update("messages", values, "message_id = ?", new String[]{Integer.toString(id)});
                } else {
                    db.update("messages", values, "dialog_id = ? AND message_id = ?", new String[]{Long.toString(dialogId), Integer.toString(id)});
                }
            }
        });
    }

    public void loadDeleted(long dialogId, int minDate, int maxDate, Consumer<ArrayList<TLRPC.Message>> completion) {
        queue.execute(() -> {
            ArrayList<TLRPC.Message> result = new ArrayList<>();
            String selection = "dialog_id = ? AND deleted_at IS NOT NULL";
            ArrayList<String> arguments = new ArrayList<>();
            arguments.add(Long.toString(dialogId));
            if (minDate > 0) {
                selection += " AND date >= ?";
                arguments.add(Integer.toString(minDate));
            }
            if (maxDate > 0) {
                selection += " AND date <= ?";
                arguments.add(Integer.toString(maxDate));
            }
            try (Cursor cursor = database.getReadableDatabase().query("messages", new String[]{"data"}, selection,
                    arguments.toArray(new String[0]), null, null, "date ASC, message_id ASC")) {
                while (cursor.moveToNext()) {
                    TLRPC.Message message = deserialize(cursor.getBlob(0));
                    if (message != null) result.add(message);
                }
            }
            AndroidUtilities.runOnUIThread(() -> completion.accept(result));
        });
    }

    public void loadRevisions(long dialogId, int messageId, Consumer<ArrayList<TLRPC.Message>> completion) {
        queue.execute(() -> {
            ArrayList<TLRPC.Message> result = new ArrayList<>();
            try (Cursor cursor = database.getReadableDatabase().query("revisions", new String[]{"data"},
                    "dialog_id = ? AND message_id = ?", new String[]{Long.toString(dialogId), Integer.toString(messageId)},
                    null, null, "id ASC")) {
                while (cursor.moveToNext()) {
                    TLRPC.Message message = deserialize(cursor.getBlob(0));
                    if (message != null) result.add(message);
                }
            }
            AndroidUtilities.runOnUIThread(() -> completion.accept(result));
        });
    }

    public void removeLocal(long dialogId, int messageId) {
        queue.execute(() -> {
            SQLiteDatabase db = database.getWritableDatabase();
            db.delete("messages", "dialog_id = ? AND message_id = ?", new String[]{Long.toString(dialogId), Integer.toString(messageId)});
            db.delete("revisions", "dialog_id = ? AND message_id = ?", new String[]{Long.toString(dialogId), Integer.toString(messageId)});
        });
    }

    public void clear(long dialogId) {
        queue.execute(() -> {
            SQLiteDatabase db = database.getWritableDatabase();
            db.delete("messages", "dialog_id = ?", new String[]{Long.toString(dialogId)});
            db.delete("revisions", "dialog_id = ?", new String[]{Long.toString(dialogId)});
        });
    }

    private boolean isEligible(TLRPC.Message message) {
        if (message == null || message.id <= 0 || message.out || message.peer_id == null) return false;
        if (message instanceof TLRPC.TL_messageService || message.ttl_period != 0 || message.noforwards) return false;
        if (MessageObject.isSecretMedia(message) || MessageObject.isEphemeralAndNotWelcome(message)) return false;
        if (message.media instanceof TLRPC.TL_messageMediaPaidMedia) return false;
        long dialogId = MessageObject.getDialogId(message);
        if (dialogId < 0) {
            TLRPC.Chat chat = MessagesController.getInstance(account).getChat(-dialogId);
            if (chat != null && chat.noforwards) return false;
        }
        return dialogId != 0 && !org.telegram.messenger.DialogObject.isEncryptedDialog(dialogId);
    }

    public boolean canDisplayDeleted(TLRPC.Message message) {
        return NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext)
                .getBoolean(NagramiXSettings.SHOW_DELETED_MESSAGES, false) && isEligible(message);
    }

    private static byte[] serialize(TLRPC.Message message) {
        NativeByteBuffer buffer = null;
        try {
            buffer = new NativeByteBuffer(message.getObjectSize());
            message.serializeToStream(buffer);
            ByteBuffer copy = buffer.buffer.duplicate();
            copy.flip();
            byte[] value = new byte[copy.remaining()];
            copy.get(value);
            return value;
        } catch (Exception error) {
            FileLog.e(error);
            return null;
        } finally {
            if (buffer != null) buffer.reuse();
        }
    }

    private static TLRPC.Message deserialize(byte[] value) {
        if (value == null || value.length < 4) return null;
        NativeByteBuffer buffer = null;
        try {
            buffer = new NativeByteBuffer(value.length);
            buffer.writeBytes(value);
            buffer.position(0);
            return TLRPC.Message.TLdeserialize(buffer, buffer.readInt32(false), false);
        } catch (Exception error) {
            FileLog.e(error);
            return null;
        } finally {
            if (buffer != null) buffer.reuse();
        }
    }

    private static byte[] currentValue(SQLiteDatabase db, long dialogId, int messageId) {
        try (Cursor cursor = db.query("messages", new String[]{"data"}, "dialog_id = ? AND message_id = ?",
                new String[]{Long.toString(dialogId), Integer.toString(messageId)}, null, null, null)) {
            return cursor.moveToFirst() ? cursor.getBlob(0) : null;
        }
    }

    private static final class ArchiveDatabase extends SQLiteOpenHelper {
        ArchiveDatabase(Context context, int account) {
            super(context, "nagramix-message-archive-" + account + ".db", null, 1);
        }

        @Override
        public void onCreate(SQLiteDatabase db) {
            db.execSQL("CREATE TABLE messages (dialog_id INTEGER NOT NULL, message_id INTEGER NOT NULL, date INTEGER NOT NULL, data BLOB NOT NULL, deleted_at INTEGER, PRIMARY KEY(dialog_id, message_id))");
            db.execSQL("CREATE INDEX messages_deleted ON messages(dialog_id, deleted_at, date)");
            db.execSQL("CREATE TABLE revisions (id INTEGER PRIMARY KEY AUTOINCREMENT, dialog_id INTEGER NOT NULL, message_id INTEGER NOT NULL, observed_at INTEGER NOT NULL, data BLOB NOT NULL)");
            db.execSQL("CREATE INDEX revisions_message ON revisions(dialog_id, message_id, id)");
        }

        @Override
        public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        }
    }
}
