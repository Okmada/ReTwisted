try:
    import PyInstaller.__main__
except ImportError:
    print("PyInstaller not installed")
    exit(1)

PyInstaller.__main__.run([
    "src/main.py",
    "--onefile",
    "--noconsole",
    "-n", "ReTwisted",
    "-i=assets/icon.png",
    "--add-data=assets/icon.png;assets",
    "--add-data=assets/samples.data;assets",
    "--add-data=assets/samples-twisted1_19_1.data;assets",
])