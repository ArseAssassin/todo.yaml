{
  description = "todo.yaml CLI";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-23.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem
      (system:
        let
          pkgs = import nixpkgs {
            inherit system;
          };
        in
        with pkgs;
        {
          devShells.default = mkShell {
            # shellHook = ''
            #   python -mvenv .venv
            #   source .venv/bin/activate
            #   python -mpip install -r requirements.txt
            #   export PATH="${self}/bin:$PATH"
            # '';
            packages = [
              python311
              python311Packages.click
              python311Packages.colorama
              python311Packages.ruyaml
              python311Packages.jq
            ];
          };

          packages = rec {
            todo-yaml = python311Packages.buildPythonApplication {
              propagatedBuildInputs = [
                (python311.withPackages (ps: with ps; [
                  click
                  colorama
                  ruyaml
                  jq
                ]))
              ];

              name = "todo-yaml";
              version = "1.0";
              src = ./.;
            };

            default = todo-yaml;
          };

          apps = rec {
            todo-yaml = flake-utils.lib.mkApp {
              drv = self.packages.${system}.todo-yaml;
            };

            default = todo-yaml;
          };
        }
      );
}