#!/usr/bin/env python3
from pathlib import Path
import re
import sys

app = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
manifest = app / "android/app/src/main/AndroidManifest.xml"
if not manifest.exists():
    raise SystemExit(f"Android manifest not found: {manifest}")

xml = manifest.read_text(encoding="utf-8")
permission = "android.permission.POST_NOTIFICATIONS"
if permission not in xml:
    match = re.search(r"<manifest\b[^>]*>", xml)
    if not match:
        raise SystemExit("Could not locate <manifest> tag")
    xml = xml[:match.end()] + '\n    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />' + xml[match.end():]
    manifest.write_text(xml, encoding="utf-8")
print("Added POST_NOTIFICATIONS to AndroidManifest.xml")

main_files = list((app / "android/app/src/main").rglob("MainActivity.kt"))
is_kotlin = bool(main_files)
if not main_files:
    main_files = list((app / "android/app/src/main").rglob("MainActivity.java"))
if not main_files:
    raise SystemExit("MainActivity.kt/java not found")

activity = main_files[0]
source = activity.read_text(encoding="utf-8")
if permission not in source:
    if is_kotlin:
        imports = [
            "import android.Manifest",
            "import android.content.pm.PackageManager",
            "import android.os.Build",
            "import android.os.Bundle",
        ]
        package = re.search(r"^package\s+[^\n]+", source, re.M)
        pos = package.end() if package else 0
        source = source[:pos] + "\n" + "\n".join(i for i in imports if i not in source) + "\n" + source[pos:]
        method = """
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1001)
        }
    }
"""
        if re.search(r"class\s+MainActivity[^{\n]*\{", source):
            pos = source.rfind("}")
            source = source[:pos] + method + "\n" + source[pos:]
        else:
            pattern = r"(class\s+MainActivity\s*:\s*FlutterActivity\s*\(\s*\))\s*"
            source, count = re.subn(pattern, r"\1 {\n" + method + "\n}", source, count=1)
            if count != 1:
                raise SystemExit("Could not safely add onCreate to Kotlin MainActivity")
    else:
        imports = [
            "import android.Manifest;",
            "import android.content.pm.PackageManager;",
            "import android.os.Build;",
            "import android.os.Bundle;",
        ]
        package = re.search(r"^package\s+[^\n]+;", source, re.M)
        pos = package.end() if package else 0
        source = source[:pos] + "\n" + "\n".join(i for i in imports if i not in source) + "\n" + source[pos:]
        method = """
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1001);
        }
    }
"""
        pos = source.rfind("}")
        if pos < 0:
            raise SystemExit("Could not locate Java MainActivity class body")
        source = source[:pos] + method + "\n" + source[pos:]
    activity.write_text(source, encoding="utf-8")
print(f"Added Android 13+ runtime notification permission request in {activity}")
