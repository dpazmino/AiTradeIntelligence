{pkgs}: {
  deps = [
    pkgs.mariadb
    pkgs.zlib
    pkgs.xcodebuild
    pkgs.glibcLocales
    pkgs.postgresql
    pkgs.bash
  ];
}
