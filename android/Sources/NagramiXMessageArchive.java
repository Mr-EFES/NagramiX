package com.mr_efes.nagramix;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.DialogObject;
import org.telegram.messenger.MessageObject;
import org.telegram.messenger.UserConfig;
import org.telegram.messenger.UserObject;
import org.telegram.tgnet.NativeByteBuffer;
import org.telegram.tgnet.TLRPC;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Account-local snapshots for deletions and revisions observed by this client.
 * The archive never requests missing messages or media from Telegram.
 */
public final class NagramiXMessageArchive extends SQLiteOpenHelper {
    private static final int VERSION = 1;
    private static final NagramiXMessageArchive[] INSTANCES = new NagramiXMessageArchive[UserConfig.MAX_ACCOUNT_COUNT];

    public static NagramiXMessageArchive getInstance(int account) {
        synchronized (INSTANCES) {
            if (INSTANCES[account] == null) {
                INSTANCES[account] = new NagramiXMessageArchive(ApplicationLoader.applicationContext, account);
            }
            return INSTANCES[account];
        }
    }

    private final int account;

    private NagramiXMessageArchive(Context context, int account) {
        super(context, "nagramix-message-archive-" + account + ".db", null, VERSION);
        this.account = account;
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE messages(dialog_id INTEGER NOT NULL, message_id INTEGER NOT NULL, body BLOB NOT NULL, deleted_at INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(dialog_id, message_id))");
        db.execSQL("CREATE TABLE revisions(dialog_id INTEGER NOT NULL, message_id INTEGER NOT NULL, observed_at INTEGER NOT NULL, body BLOB NOT NULL, UNIQUE(dialog_id, message_id, observed_at, body))");
        db.execSQL("CREATE INDEX revisions_message ON revisions(dialog_id, message_id, observed_at)");
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        // Version one has no migrations.
    }

    private boolean enabled(String key) {
        return NagramiXSettings.INSTANCE.preferences(ApplicationLoader.applicationContext)
                .getBoolean(key, NagramiXSettings.booleanDefault(key));
    }

    private boolean eligible(long dialogId, TLRPC.Message message) {
        if (message == null || message.id <= 0 || message.out || message.noforwards) {
            return false;
        }
        if (dialogId == 0 || dialogId == UserConfig.getInstance(account).getClientUserId()
                || dialogId == UserObject.VERIFY || DialogObject.isEncryptedDialog(dialogId)) {
            return false;
        }
        if (message.ttl != 0 || message.ttl_period != 0 || message.destroyTime != 0
                || message.expire_date != 0 || MessageObject.isSecretMedia(message)) {
            return false;
        }
        return !(MessageObject.getMedia(message) instanceof TLRPC.TL_messageMediaPaidMedia);
    }

    private static byte[] serialize(TLRPC.Message message) {
        NativeByteBuffer buffer = null;
        try {
            buffer = new NativeByteBuffer(message.getObjectSize());
            message.serializeToStream(buffer);
            return buffer.toByteArray();
        } catch (Exception ignore) {
            return null;
        } finally {
            if (buffer != null) {
                buffer.reuse();
            }
        }
    }

    private static TLRPC.Message deserialize(byte[] bytes) {
        if (bytes == null) {
            return null;
        }
        NativeByteBuffer buffer = null;
        try {
            buffer = new NativeByteBuffer(bytes.length);
            buffer.writeBytes(bytes);
            buffer.position(0);
            return TLRPC.Message.TLdeserialize(buffer, buffer.readInt32(false), false);
        } catch (Exception ignore) {
            return null;
        } finally {
            if (buffer != null) {
                buffer.reuse();
            }
        }
    }

    private void captureIfMissing(SQLiteDatabase db, long dialogId, TLRPC.Message message) {
        if (!eligible(dialogId, message)) {
            return;
        }
        byte[] body = serialize(message);
        if (body == null) {
            return;
        }
        ContentValues values = new ContentValues();
        values.put("dialog_id", dialogId);
        values.put("message_id", message.id);
        values.put("body", body);
        db.insertWithOnConflict("messages", null, values, SQLiteDatabase.CONFLICT_IGNORE);
    }

    public synchronized void captureLoaded(long dialogId, List<MessageObject> messages) {
        if (!enabled(NagramiXSettings.SHOW_DELETED_MESSAGES) && !enabled(NagramiXSettings.EDIT_HISTORY)) {
            return;
        }
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransaction();
        try {
            for (MessageObject object : messages) {
                if (object != null) {
                    captureIfMissing(db, dialogId, object.messageOwner);
                }
            }
            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
    }

    public synchronized void captureIncoming(List<TLRPC.Message> messages) {
        if (!enabled(NagramiXSettings.SHOW_DELETED_MESSAGES) && !enabled(NagramiXSettings.EDIT_HISTORY)) {
            return;
        }
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransaction();
        try {
            for (TLRPC.Message message : messages) {
                if (message != null) {
                    captureIfMissing(db, MessageObject.getDialogId(message), message);
                }
            }
            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
    }

    public synchronized void recordEdits(long dialogId, List<MessageObject> replacements,
                                         android.util.SparseArray<MessageObject> current) {
        if (!enabled(NagramiXSettings.EDIT_HISTORY)) {
            return;
        }
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransaction();
        try {
            for (MessageObject replacement : replacements) {
                MessageObject previous = replacement == null ? null : current.get(replacement.getId());
                if (previous == null || !eligible(dialogId, previous.messageOwner)
                        || !eligible(dialogId, replacement.messageOwner)
                        || sameContent(previous.messageOwner, replacement.messageOwner)) {
                    continue;
                }
                captureIfMissing(db, dialogId, previous.messageOwner);
                byte[] revision = serialize(previous.messageOwner);
                if (revision != null) {
                    ContentValues values = new ContentValues();
                    values.put("dialog_id", dialogId);
                    values.put("message_id", previous.getId());
                    values.put("observed_at", Math.max(replacement.messageOwner.edit_date, replacement.messageOwner.date));
                    values.put("body", revision);
                    db.insertWithOnConflict("revisions", null, values, SQLiteDatabase.CONFLICT_IGNORE);
                }
                byte[] currentBody = serialize(replacement.messageOwner);
                if (currentBody != null) {
                    ContentValues values = new ContentValues();
                    values.put("body", currentBody);
                    db.update("messages", values, "dialog_id=? AND message_id=?",
                            new String[]{Long.toString(dialogId), Integer.toString(previous.getId())});
                }
            }
            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
    }

    private static boolean sameContent(TLRPC.Message first, TLRPC.Message second) {
        if (!java.util.Objects.equals(first.message, second.message)) {
            return false;
        }
        return java.util.Arrays.equals(serializeEntitiesAndMedia(first), serializeEntitiesAndMedia(second));
    }

    private static byte[] serializeEntitiesAndMedia(TLRPC.Message message) {
        NativeByteBuffer buffer = null;
        try {
            int size = 4;
            for (TLRPC.MessageEntity entity : message.entities) size += entity.getObjectSize();
            if (MessageObject.getMedia(message) != null) size += MessageObject.getMedia(message).getObjectSize();
            buffer = new NativeByteBuffer(size);
            buffer.writeInt32(message.entities.size());
            for (TLRPC.MessageEntity entity : message.entities) entity.serializeToStream(buffer);
            if (MessageObject.getMedia(message) != null) MessageObject.getMedia(message).serializeToStream(buffer);
            return buffer.toByteArray();
        } catch (Exception ignore) {
            return null;
        } finally {
            if (buffer != null) buffer.reuse();
        }
    }

    /** Returns only ids Telegram should still remove from the visible chat. */
    public synchronized ArrayList<Integer> archiveDeletion(long dialogId, List<Integer> ids,
                                                            android.util.SparseArray<MessageObject> current) {
        ArrayList<Integer> remaining = new ArrayList<>(ids);
        if (!enabled(NagramiXSettings.SHOW_DELETED_MESSAGES)) {
            return remaining;
        }
        SQLiteDatabase db = getWritableDatabase();
        long deletedAt = System.currentTimeMillis() / 1000L;
        for (Integer id : ids) {
            MessageObject object = current.get(id);
            if (object == null || !eligible(dialogId, object.messageOwner)) {
                continue;
            }
            captureIfMissing(db, dialogId, object.messageOwner);
            ContentValues values = new ContentValues();
            values.put("deleted_at", deletedAt);
            if (db.update("messages", values, "dialog_id=? AND message_id=?",
                    new String[]{Long.toString(dialogId), Integer.toString(id)}) != 0) {
                remaining.remove(id);
            }
        }
        return remaining;
    }

    public synchronized void markDeleted(long dialogId, List<Integer> ids) {
        if (!enabled(NagramiXSettings.SHOW_DELETED_MESSAGES) || dialogId == 0) {
            return;
        }
        SQLiteDatabase db = getWritableDatabase();
        ContentValues values = new ContentValues();
        values.put("deleted_at", System.currentTimeMillis() / 1000L);
        for (Integer id : ids) {
            db.update("messages", values, "dialog_id=? AND message_id=?",
                    new String[]{Long.toString(dialogId), Integer.toString(id)});
        }
    }

    public synchronized void mergeDeleted(long dialogId, ArrayList<MessageObject> destination) {
        if (!enabled(NagramiXSettings.SHOW_DELETED_MESSAGES)) {
            return;
        }
        Set<Integer> present = new HashSet<>();
        for (MessageObject object : destination) present.add(object.getId());
        try (Cursor cursor = getReadableDatabase().query("messages", new String[]{"message_id", "body"},
                "dialog_id=? AND deleted_at>0", new String[]{Long.toString(dialogId)}, null, null, null)) {
            while (cursor.moveToNext()) {
                int id = cursor.getInt(0);
                if (present.contains(id)) continue;
                TLRPC.Message message = deserialize(cursor.getBlob(1));
                if (message == null) continue;
                String marker = "\n" + org.telegram.messenger.LocaleController.getString(org.telegram.messenger.R.string.NagramiXDeletedMarker);
                message.message = (message.message == null ? "" : message.message) + marker;
                destination.add(new MessageObject(account, message, true, false));
                present.add(id);
            }
        }
    }

    public synchronized ArrayList<TLRPC.Message> revisions(long dialogId, int messageId) {
        ArrayList<TLRPC.Message> result = new ArrayList<>();
        if (!enabled(NagramiXSettings.EDIT_HISTORY)) return result;
        try (Cursor cursor = getReadableDatabase().query("revisions", new String[]{"body"},
                "dialog_id=? AND message_id=?", new String[]{Long.toString(dialogId), Integer.toString(messageId)},
                null, null, "observed_at ASC")) {
            while (cursor.moveToNext()) {
                TLRPC.Message message = deserialize(cursor.getBlob(0));
                if (message != null) result.add(message);
            }
        }
        return result;
    }

    public synchronized void clearAll() {
        SQLiteDatabase db = getWritableDatabase();
        db.delete("revisions", null, null);
        db.delete("messages", null, null);
    }
}
