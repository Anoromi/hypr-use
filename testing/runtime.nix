let pkgs = import /nix/store/c60zr86cdk6xm190q1h1iq06n45m3p8n-0zfsjx62jhgjl5xpsrqalcarxq1ik1b2-source { system = "x86_64-linux"; }; in pkgs.buildEnv {
  name = "hypr-use-test-runtime";
  paths = [ (import ./test-seat.nix { inherit pkgs; }) (pkgs.cage.overrideAttrs (old: { postPatch = (old.postPatch or "") + ''
    substituteInPlace cage.c --replace-fail 'wlr_xdg_shell_create(server.wl_display, 5)' 'wlr_xdg_shell_create(server.wl_display, 6)'
  ''; })) (pkgs.python3.withPackages (p: [ p.pygobject3 ])) pkgs.gtk3 ];
}
