"""Pinned AutoJs6 bridge constructor decoupling; not an engine integration.
Preserves upstream constructor and service/permission behavior.
Input is app/src/main/java/org/autojs/autojs/core/accessibility/AccessibilityBridgeImpl.java.
"""
import argparse
from pathlib import Path

OLD = '''    public AccessibilityBridgeImpl(AbstractAutoJs autoJs) {
        super(autoJs.getApplicationContext(), new AccessibilityConfig(), autoJs.getUiHandler());
        mAutoJs = autoJs;
    }'''
NEW = '''    public AccessibilityBridgeImpl(AbstractAutoJs autoJs) {
        this(autoJs.getApplicationContext(), autoJs.getUiHandler(),
                autoJs.getInfoProvider(), autoJs.getNotificationObserver());
    }

    /** Host-supplied dependencies; does not start or grant an accessibility service. */
    public AccessibilityBridgeImpl(android.content.Context context,
                                   org.autojs.autojs.tool.UiHandler uiHandler,
                                   ActivityInfoProvider infoProvider,
                                   AccessibilityNotificationObserver notificationObserver) {
        super(context, new AccessibilityConfig(), uiHandler);
        mInfoProvider = java.util.Objects.requireNonNull(infoProvider);
        mNotificationObserver = java.util.Objects.requireNonNull(notificationObserver);
    }'''

def transform(text):
    replacements = {
        '    private final AbstractAutoJs mAutoJs;':
        '    private final ActivityInfoProvider mInfoProvider;\n    private final AccessibilityNotificationObserver mNotificationObserver;',
        OLD: NEW,
        'return mAutoJs.getInfoProvider();': 'return mInfoProvider;',
        'return mAutoJs.getNotificationObserver();': 'return mNotificationObserver;',
    }
    for old in replacements:
        if text.count(old) != 1:
            raise ValueError('AutoJs bridge anchor mismatch: ' + old[:80])
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError('Refusing to overwrite output')
    result = transform(args.source.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result)
