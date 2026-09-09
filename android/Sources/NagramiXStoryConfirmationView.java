package org.telegram.ui.Stories;

import android.content.Context;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ContactsController;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.MessagesController;
import org.telegram.messenger.R;
import org.telegram.tgnet.TLRPC;
import org.telegram.tgnet.tl.TL_stories;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Components.BackupImageView;
import org.telegram.ui.Components.LayoutHelper;

/** Full-screen, non-playing cached-thumbnail privacy gate for one Story id. */
final class NagramiXStoryConfirmationView extends FrameLayout {
    private final Runnable cancelled;

    NagramiXStoryConfirmationView(Context context, int account, long dialogId, TL_stories.StoryItem story, Runnable confirmed, Runnable cancelled) {
        super(context);
        this.cancelled = cancelled;
        setClickable(true);
        setFocusableInTouchMode(true);

        BackupImageView preview = new BackupImageView(context);
        preview.setBlurAllowed(true);
        preview.setHasBlur(true);
        preview.getImageReceiver().setAspectFit(false);
        StoriesUtilities.setImage(preview.getImageReceiver(), story, "720_1280_b3");
        addView(preview, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.MATCH_PARENT));

        View scrim = new View(context);
        scrim.setBackgroundColor(Theme.getColor(Theme.key_chat_BlurAlpha));
        addView(scrim, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.MATCH_PARENT));

        ImageView close = new ImageView(context);
        close.setImageResource(R.drawable.ic_close_white);
        close.setColorFilter(Theme.getColor(Theme.key_featuredStickers_buttonText));
        close.setScaleType(ImageView.ScaleType.CENTER);
        close.setContentDescription(LocaleController.getString(R.string.Close));
        close.setOnClickListener(v -> cancel());
        addView(close, LayoutHelper.createFrame(56, 56, Gravity.TOP | Gravity.RIGHT, 0, 8, 8, 0));

        LinearLayout panel = new LinearLayout(context);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setGravity(Gravity.CENTER_HORIZONTAL);
        TextView title = text(context, LocaleController.getString(R.string.NagramiXStoryConfirmTitle), 24, Theme.key_featuredStickers_buttonText);
        title.setGravity(Gravity.CENTER);
        panel.addView(title, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 0, 0, 12));
        TextView body = text(context, LocaleController.formatString(R.string.NagramiXStoryConfirmText, peerName(account, dialogId)), 16, Theme.key_featuredStickers_buttonText);
        body.setGravity(Gravity.CENTER);
        panel.addView(body, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, 0, 0, 0, 28));
        TextView button = text(context, LocaleController.getString(R.string.NagramiXStoryConfirmAction), 17, Theme.key_featuredStickers_buttonText);
        button.setGravity(Gravity.CENTER);
        button.setBackground(Theme.createSimpleSelectorRoundRectDrawable(AndroidUtilities.dp(12), Theme.getColor(Theme.key_featuredStickers_addButton), Theme.getColor(Theme.key_featuredStickers_addButtonPressed)));
        button.setOnClickListener(v -> { AndroidUtilities.removeFromParent(this); confirmed.run(); });
        panel.addView(button, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, 52));
        addView(panel, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, Gravity.CENTER, 32, 0, 32, 0));
        requestFocus();
    }

    private static TextView text(Context context, String value, int size, int colorKey) {
        TextView view = new TextView(context);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(Theme.getColor(colorKey));
        return view;
    }

    private static String peerName(int account, long dialogId) {
        if (dialogId > 0) {
            TLRPC.User user = MessagesController.getInstance(account).getUser(dialogId);
            return user == null ? "" : ContactsController.formatName(user.first_name, user.last_name);
        }
        TLRPC.Chat chat = MessagesController.getInstance(account).getChat(-dialogId);
        return chat == null ? "" : chat.title;
    }

    boolean cancel() {
        AndroidUtilities.removeFromParent(this);
        cancelled.run();
        return true;
    }
}
