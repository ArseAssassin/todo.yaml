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
            packages = with python311Packages; [
              python311
              python-dateutil
              pylint
              click
              colorama
              ruyaml
              jq
              pytz
            ];
          };

          packages = rec {
            todo-yaml = python311Packages.buildPythonApplication {
              propagatedBuildInputs = [
                (python311.withPackages (ps: with ps; [
                  python-dateutil
                  click
                  colorama
                  ruyaml
                  jq
                  pytz
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