# TLA+ CLI Setup on macOS

This project uses the TLA+ command-line model checker, TLC, through `tla2tools.jar`.

## Install Java

TLC runs on the JVM. Install a recent JDK:

```sh
brew install openjdk
```

Check it:

```sh
java -version
```

## Download TLA+ tools

Download `tla2tools.jar` from the official TLA+ tools releases:

https://github.com/tlaplus/tlaplus/releases

The release page includes `tla2tools.jar` assets and checksums. The repository also notes that command-line TLC is the recommended path over relying on the older Toolbox UI.

One simple local layout:

```sh
mkdir -p "$HOME/tools/tlaplus"
curl -L -o "$HOME/tools/tlaplus/tla2tools.jar" \
  "https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar"
```

If you choose a newer release, replace the URL with the `tla2tools.jar` asset URL from the release page.

## Configure the environment

Add this to your shell profile:

```sh
export TLA_HOME="$HOME/tools/tlaplus"
export TLAPLUS_JAR="$TLA_HOME/tla2tools.jar"
```

Reload your shell and check:

```sh
test -f "$TLAPLUS_JAR" && echo "TLA+ tools configured"
```

## Run TLC manually

After this project generates artifacts, translate the PlusCal source:

```sh
java -cp "$TLAPLUS_JAR" pcal.trans -nocfg FinanceSafety_RUN.tla
```

Then run TLC:

```sh
java -cp "$TLAPLUS_JAR" tlc2.TLC -config FinanceSafety_RUN.cfg FinanceSafety_RUN.tla
```

The safety CLI runs both commands automatically when `TLAPLUS_JAR` or `TLA_HOME` is configured.
