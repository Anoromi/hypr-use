{
  description = "Hypr-use CUA MCP and benchmark";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    portal-src = {
      url = "github:gfhdhytghd/Hypr-Agent-Portal/bc0b100719dafb8bdf893ace4d3be1d78b1a0876";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, portal-src }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in {
      packages = forAllSystems (pkgs:
        let
          lib = pkgs.lib;
          python = pkgs.python3.withPackages (p: [ p.pygobject3 p.pillow ]);
          typelibPath = lib.makeSearchPath "lib/girepository-1.0" [
            pkgs.at-spi2-core pkgs.gdk-pixbuf pkgs.gtk3 pkgs.libdbusmenu-gtk3
            pkgs.gobject-introspection
          ];
          runtimePath = lib.makeBinPath [
            pkgs.nodejs_22 python pkgs.hyprland pkgs.ffmpeg pkgs.grim pkgs.wtype
            pkgs.wl-clipboard
          ];
          portalRuntime = pkgs.stdenvNoCC.mkDerivation {
            pname = "hypr-use-portal-runtime";
            version = "0.56.2";
            src = portal-src;
            patches = [ ./vendor/portal-checkpoint.patch ./nix/portal-mcp-runtime.patch ];
            installPhase = ''
              mkdir -p $out/mcp $out/scripts
              cp mcp/*.py $out/mcp/
              cp scripts/hypr-agent-portalctl $out/scripts/
            '';
          };
          mcp = pkgs.buildNpmPackage {
            pname = "hypr-use-mcp";
            version = "0.2.0";
            src = ./mcp/unified;
            npmDepsHash = "sha256-LCUHSMnmvRlagTS7glgno+fkfDIg3wufQg9cCloDcBk=";
            dontNpmBuild = true;
            nativeBuildInputs = [ pkgs.makeWrapper ];
            installPhase = ''
              runHook preInstall
              root=$out/lib/hypr-use
              mkdir -p "$root/mcp/unified" "$root/vendor/hypr-agent-portal-0.56.2" "$root/testing" "$root/research/2026-09-12" $out/bin
              cp -r *.mjs *.py package.json node_modules "$root/mcp/unified/"
              cp ${./mcp/server.py} "$root/mcp/server.py"
              cp ${./mcp/tools.json} "$root/mcp/tools.json"
              cp ${./testing/portal-timing.py} "$root/testing/portal-timing.py"
              cp ${./research/2026-09-12/unified-mcp-tools.json} "$root/research/2026-09-12/unified-mcp-tools.json"
              ln -s ${portalRuntime}/mcp "$root/vendor/hypr-agent-portal-0.56.2/mcp"
              cp ${./nix/backend-launch.py} "$root/mcp/unified/backend-launch.py"
              cp ${./nix/hypr-use-mcp.py} $out/bin/hypr-use-mcp
              chmod +x $out/bin/hypr-use-mcp
              substituteInPlace $out/bin/hypr-use-mcp \
                --replace-fail '@PYTHON@' '${python}/bin/python3' \
                --replace-fail '@NODE@' '${pkgs.nodejs_22}/bin/node' \
                --replace-fail '@SERVER@' "$root/mcp/unified/server.mjs" \
                --replace-fail '@PATH@' '${runtimePath}' \
                --replace-fail '@TYPELIB_PATH@' '${typelibPath}'
              runHook postInstall
            '';
          };
          bench = pkgs.stdenvNoCC.mkDerivation {
            pname = "cua-bench";
            version = "0.1.0";
            src = ./bench;
            nativeBuildInputs = [ pkgs.makeWrapper ];
            installPhase = ''
              mkdir -p $out/lib/hypr-use/bench $out/bin
              cp -r bench cua_bench apps demo-project tasks.json real-tasks.json generate_tasks.py "$out/lib/hypr-use/bench/"
              makeWrapper ${python}/bin/python3 $out/bin/bench \
                --add-flags "$out/lib/hypr-use/bench/bench" \
                --prefix PYTHONPATH : "$out/lib/hypr-use/bench" \
                --prefix PATH : '${runtimePath}' \
                --set HYPR_USE_PACKAGED_MCP '${mcp}/bin/hypr-use-mcp' \
                --set HYPR_USE_MCP_ROOT '${mcp}/lib/hypr-use' \
                --set HYPR_USE_PACKAGED_BENCH 1
            '';
          };
        in {
          default = mcp;
          hypr-use-mcp = mcp;
          bench = bench;
        });
      apps = forAllSystems (pkgs: {
        default = { type = "app"; program = "${self.packages.${pkgs.stdenv.hostPlatform.system}.hypr-use-mcp}/bin/hypr-use-mcp"; };
        bench = { type = "app"; program = "${self.packages.${pkgs.stdenv.hostPlatform.system}.bench}/bin/bench"; };
      });
    };
}
