with import <nixpkgs> { };
let
  dontCheckPython = drv: drv.overridePythonAttrs (old: { doCheck = false; });
  pythonPackages = python312Packages;

  harfbuzz_self = harfbuzz.override { withCoreText = true; };
  ld_packages = [
    harfbuzz_self
    harfbuzz_self.dev
    imagemagick
    gdal
    geos
    cairo
    glib.out
    pango
    fontconfig.lib
    libspatialite
    file
    ghostscript
    postgresql.lib
    mupdf
    gettext
  ];
in
pkgs.mkShell {
  name = "fds";
  shellHook = ''
    echo "Launching fds shell"
    export FRAGDENSTAAT_DYLD_LIBRARY_PATH=${builtins.concatStringsSep ":" (map (x: x + "/lib") ld_packages)}
    export LD_LIBRARY_PATH=$FRAGDENSTAAT_DYLD_LIBRARY_PATH:$LD_LIBRARY_PATH
    export DYLD_LIBRARY_PATH=$FRAGDENSTAAT_DYLD_LIBRARY_PATH:$DYLD_LIBRARY_PATH

    source fds-env/bin/activate

    export CPATH="$CPATH:${mupdf.dev}/include/mupdf"
    export PYTHONBREAKPOINT=ipdb.set_trace
    export GDAL_LIBRARY_PATH=${gdal}/lib/libgdal.dylib
    export GEOS_LIBRARY_PATH=${geos}/lib/libgeos_c.dylib
    
    export CPLUS_INCLUDE_PATH="$CPLUS_INCLUDE_PATH:${libcxx.dev}/include"
    
    export CFLAGS="-stdlib=libc++ -DUSE_STD_NAMESPACE -I${libcxx.dev}/include/c++/v1"
    export MACOSX_DEPLOYMENT_TARGET=10.9

    export MAGICK_HOME="${imagemagick}"
  '';
  buildInputs = [
    uv
    pythonPackages.python
    gdal
    pythonPackages.gdal
    pythonPackages.tkinter
    pythonPackages.magic
    # pythonPackages.ocrmypdf
    # pythonPackages.weasyprint
    pnpm_9

    pkg-config
    geos
    cairo
    pango
    gettext
    harfbuzz_self
    imagemagick
    poppler_utils
    libspatialite
    file
    qpdf
    chromedriver
    git-crypt
    postgresql_14
    postgresql14Packages.postgis
    gdal
    mupdf

    glib
    libcxx
    cmake

    stripe-cli
  ] ++ (lib.optional stdenv.isDarwin pkgs.darwin.apple_sdk.frameworks.CoreText);
}
