# Pacefinder icon set

Drop final artwork here before cutting a release. The build pipeline references
these paths and silently skips icons that don't exist (good for early CI runs,
not acceptable for App Store submission).

## Required files

| File | Size | Used by |
|---|---|---|
| `pacefinder.icns` | multi-size (16, 32, 64, 128, 256, 512, 1024) | macOS `.app` bundle (pacefinder.spec) |
| `pacefinder.png`  | 512 × 512 | Linux AppImage (`.DirIcon`, top-level icon) |
| `pacefinder.ico`  | multi-size (16, 32, 48, 256) | Future Windows build |

## Generating `.icns` from a master PNG

```sh
mkdir pacefinder.iconset
sips -z 16   16   master_1024.png --out pacefinder.iconset/icon_16x16.png
sips -z 32   32   master_1024.png --out pacefinder.iconset/icon_16x16@2x.png
sips -z 32   32   master_1024.png --out pacefinder.iconset/icon_32x32.png
sips -z 64   64   master_1024.png --out pacefinder.iconset/icon_32x32@2x.png
sips -z 128  128  master_1024.png --out pacefinder.iconset/icon_128x128.png
sips -z 256  256  master_1024.png --out pacefinder.iconset/icon_128x128@2x.png
sips -z 256  256  master_1024.png --out pacefinder.iconset/icon_256x256.png
sips -z 512  512  master_1024.png --out pacefinder.iconset/icon_256x256@2x.png
sips -z 512  512  master_1024.png --out pacefinder.iconset/icon_512x512.png
cp                master_1024.png      pacefinder.iconset/icon_512x512@2x.png
iconutil -c icns pacefinder.iconset -o pacefinder.icns
```
