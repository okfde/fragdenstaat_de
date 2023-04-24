with import <nixpkgs> { };
let
  dontCheckPython = drv: drv.overridePythonAttrs (old: { doCheck = false; });
  pythonPackages = python39Packages;

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
  ];
in
pkgs.mkShell {
  name = "fds";
  shellHook = ''
    echo "Launching fds shell"
    export LD_LIBRARY_PATH=${builtins.concatStringsSep ":" (map (x: x + "/lib") ld_packages)}:$LD_LIBRARY_PATH
    export DYLD_LIBRARY_PATH=$LD_LIBRARY_PATH:$DYLD_LIBRARY_PATH
    source fds-env/bin/activate
    source dslr-complete.bash
    echo ${libcxx.dev}
    export CPATH="$CPATH:${mupdf.dev}/include/mupdf"
    export PYTHONBREAKPOINT=ipdb.set_trace
    # export DATABASE_URL=postgis://fragdenstaat_de:fragdenstaat_de@localhost:5432/fragdenstaat_de
    export GDAL_LIBRARY_PATH=${gdal}/lib/libgdal.dylib
    export GEOS_LIBRARY_PATH=${geos}/lib/libgeos_c.dylib
    
    export CPLUS_INCLUDE_PATH="$CPLUS_INCLUDE_PATH:${libcxx.dev}/include"
    
    export CFLAGS="-stdlib=libc++ -DUSE_STD_NAMESPACE -I${libcxx.dev}/include/c++/v1"
    export MACOSX_DEPLOYMENT_TARGET=10.9
  '';
  buildInputs = [
    pythonPackages.python
    gdal
    pythonPackages.gdal
    pythonPackages.tkinter
    pythonPackages.keras
    pythonPackages.magic
    pythonPackages.ocrmypdf
    pythonPackages.weasyprint
    #pythonPackages.tensorflow
    
    pkgconfig
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

    # magic-wormhole
    # ansible
    # boost.dev
  ];
}
