#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  TELEGRAM HOOKER — plug & play
#  One step only: bash /sdcard/Download/start.sh
#  Everything is automatic: extract + run — no internet needed
# ============================================================
set -u

APP=/sdcard/Download
LIBS=$APP/libs
ROOT=$HOME/tool
DEST=$ROOT/debian/debian-bookworm-aarch64
PIP_MARKER="$DEST/.pip_installed_v2"

PY311="$DEST/usr/bin/python3.11"
PY311_ROOTFS="/usr/bin/python3.11"

_e() { echo "$1"; }

run_rootfs() {
    unset LD_PRELOAD
    unset ANDROID_PINNED_TOOLS
    "$PREFIX/bin/proot" -0 \
        -r "$DEST" \
        -b /proc -b /dev -b /sys \
        -b /system:/system \
        -b /vendor:/vendor \
        -b /apex:/apex \
        -b /sdcard:/sdcard \
        -w "$APP" \
        "$@"
}

start_pulse() {
    PA_SOCKET=""
    PA_MODE=""
    if ! command -v pulseaudio >/dev/null 2>&1; then
        _e "     Installing PulseAudio..."
        pkg install -y pulseaudio >> "$ROOT/pip_install.log" 2>&1
    fi
    if command -v pulseaudio >/dev/null 2>&1; then
        pulseaudio --kill 2>/dev/null
        sleep 0.5
        pulseaudio --start \
            --load="module-native-protocol-unix auth-anonymous=1" \
            --load="module-sles-sink sink_name=android_out" \
            --load="module-sles-source source_name=android_in" \
            --exit-idle-time=-1 2>/dev/null
        sleep 2
        if pulseaudio --check 2>/dev/null; then
            PA_MODE="real"
        else
            pulseaudio --start \
                --load="module-native-protocol-unix auth-anonymous=1" \
                --load="module-null-sink sink_name=virtual sink_properties=device.description=VirtualSpeaker" \
                --load="module-always-source source_name=virtual_source source_properties=device.description=VirtualMic" \
                --exit-idle-time=-1 2>/dev/null
            sleep 2
            if pulseaudio --check 2>/dev/null; then
                PA_MODE="virtual"
            fi
        fi
        if pulseaudio --check 2>/dev/null; then
            for candidate in \
                "$PREFIX/var/run/pulse/native" \
                "${XDG_RUNTIME_DIR:-}/pulse/native" \
                "$HOME/.pulse/native" ; do
                if [ -S "$candidate" ]; then
                    PA_SOCKET="$candidate"
                    break
                fi
            done
        fi
    fi
}

rootfs_complete() {
    [ -x "$PY311" ] &&
    [ "$(stat -c%s "$PY311" 2>/dev/null || echo 0)" -gt 5000000 ] &&
    [ -e "$DEST/lib/ld-linux-aarch64.so.1" ] &&
    [ -e "$DEST/usr/lib/aarch64-linux-gnu/libc.so.6" ] &&
    [ -e "$DEST/usr/lib/python3/dist-packages/pyrogram/__init__.py" ]
}

banner() {
    echo ""
    echo "==========================================================="
    echo "       ████████ ██    ██ ██   ██ ██  ██████ "
    echo "          ██    ██    ██ ██  ██  ██ ██   ██ "
    echo "          ██    ██    ██ █████   ██ ██   ██ "
    echo "          ██    ██    ██ ██ ██  ██ ██   ██ "
    echo "          ██     ██████  ██  ██ ██  ██████ "
    echo "   ... everything is prepared for you automatically"
    echo "==========================================================="
    echo ""
}

storage_ok() {
    [ -d "$APP" ] && [ -r "$APP" ] && [ -d "$LIBS" ]
}

setup_all() {
    if storage_ok; then
        _e "[1/4] Storage access granted"
    else
        _e "[1/4] Grant storage access (tap Allow when prompted)"
        ( timeout 25 termux-setup-storage 2>/dev/null ) &
        TPID=$!
        for i in $(seq 1 30); do
            kill -0 $TPID 2>/dev/null || break
            if storage_ok; then break; fi
            sleep 1
        done
        kill $TPID 2>/dev/null
        wait $TPID 2>/dev/null
        if storage_ok; then
            _e "     Ready"
        else
            _e "     Permission may be denied, storage not granted yet"
        fi
    fi
    sleep 1

    if [ ! -f "$LIBS/rootfs.tar.gz" ] || [ ! -f "$LIBS/proot.deb" ]; then
        echo ""
        _e "Missing libs or files not downloaded"
        _e "Please check: $APP"
        _e "then try again: bash /sdcard/Download/start.sh"
        return 1
    fi

    _e "[2/4] Extracting system"
    if ! rootfs_complete; then
        _e "     (This may take 1-3 minutes)"
        gzip -t "$LIBS/rootfs.tar.gz" >/dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo ""
            _e "The file rootfs.tar.gz may be corrupted"
            return 1
        fi
        FREE_KB=$(df -k "$HOME" 2>/dev/null | awk 'NR==2{print $4}')
        NEED_KB=900000
        if [ -n "$FREE_KB" ] && [ "$FREE_KB" -lt "$NEED_KB" ]; then
            echo ""
            _e "Not enough space. At least ~900 MB free required"
            return 1
        fi
        [ -d "$DEST" ] && rm -rf "$DEST"
        mkdir -p "$ROOT/debian"
        tar -xzf "$LIBS/rootfs.tar.gz" -C "$ROOT/debian" > "$ROOT/extract.log" 2>&1 &
        TARPID=$!
        while kill -0 $TARPID 2>/dev/null; do
            if [ -d "$DEST" ]; then
                CUR=$(du -sk "$DEST" 2>/dev/null | awk '{print $1}')
                MB=$((CUR / 1024))
                printf '\r   %d MB ...' "$MB"
            fi
            sleep 1
        done
        wait $TARPID
        echo ""
        rm -f "$PIP_MARKER"
    fi
    if ! rootfs_complete; then
        echo ""
        _e "Failed to extract system"
        echo ""
        _e "----- More details below -----"
        tail -n 5 "$ROOT/extract.log" 2>/dev/null
        echo ""
        _e "The file rootfs.tar.gz may be corrupted"
        return 1
    fi
    _e "     System ready"

    _e "[3/4] Installing audio support"
    _e "     Installing audio debs..."
    for deb in "$LIBS"/libasound2*.deb "$LIBS"/libpulse*.deb "$LIBS"/libsndfile*.deb "$LIBS"/libportaudio*.deb "$LIBS"/libjack*.deb; do
        [ -f "$deb" ] || continue
        _e "       $(basename "$deb")"
        dpkg-deb -x "$deb" "$DEST" 2>/dev/null
    done
    ln -sf libportaudio.so.2.0.0 "$DEST/usr/lib/aarch64-linux-gnu/libportaudio.so.2" 2>/dev/null
    ln -sf libportaudio.so.2.0.0 "$DEST/usr/lib/aarch64-linux-gnu/libportaudio.so" 2>/dev/null
    run_rootfs /usr/bin/ldconfig 2>/dev/null
    run_rootfs /sbin/ldconfig 2>/dev/null
    mkdir -p "$DEST/root" 2>/dev/null
    cat > "$DEST/root/.asoundrc" << 'ALSA'
pcm.!default {
    type pulse
}
ctl.!default {
    type pulse
}
ALSA
    _e "     Audio support ready"

    _e "[4/4] Installing Python libraries"
    if [ -f "$PIP_MARKER" ]; then
        if run_rootfs "$PY311_ROOTFS" -c "import pyrogram; import ntgcalls; import sounddevice; print('OK')" 2>/dev/null | grep -q OK; then
            _e "     Already installed"
        else
            rm -f "$PIP_MARKER"
        fi
    fi
    if [ ! -f "$PIP_MARKER" ]; then
        PIP_LOG="$ROOT/pip_install.log"
        : > "$PIP_LOG"

        run_rootfs "$PY311_ROOTFS" -m pip install \
            --no-index --find-links "$LIBS" \
            --disable-pip-version-check \
            --break-system-packages \
            pyrogram pyaes >> "$PIP_LOG" 2>&1

        run_rootfs "$PY311_ROOTFS" -m pip install \
            --no-index --find-links "$LIBS" \
            --disable-pip-version-check \
            --break-system-packages \
            py-tgcalls==2.2.0 --no-deps >> "$PIP_LOG" 2>&1

        run_rootfs "$PY311_ROOTFS" -m pip install \
            --no-index --find-links "$LIBS" \
            --disable-pip-version-check \
            --break-system-packages \
            ntgcalls==2.2.5 >> "$PIP_LOG" 2>&1

        run_rootfs "$PY311_ROOTFS" -m pip install \
            --no-index --find-links "$LIBS" \
            --disable-pip-version-check \
            --break-system-packages \
            aiohttp >> "$PIP_LOG" 2>&1

        run_rootfs "$PY311_ROOTFS" -m pip install \
            --no-index --find-links "$LIBS" \
            --disable-pip-version-check \
            --break-system-packages \
            pycparser cffi sounddevice 2>&1 | while read line; do
            _e "       pip-sd: $line"
        done

        if run_rootfs "$PY311_ROOTFS" -c "import pyrogram; import ntgcalls; print('OK')" 2>/dev/null | grep -q OK; then
            touch "$PIP_MARKER"
            _e "     Libraries ready"
        else
            _e "     Retrying all dependencies..."
                run_rootfs "$PY311_ROOTFS" -m pip install \
                --no-index --find-links "$LIBS" \
                --disable-pip-version-check \
                --break-system-packages \
                pyrogram pyaes py-tgcalls==2.2.0 ntgcalls==2.2.5 aiohttp pycparser cffi sounddevice >> "$PIP_LOG" 2>&1
            if run_rootfs "$PY311_ROOTFS" -c "import pyrogram; import ntgcalls; print('OK')" 2>/dev/null | grep -q OK; then
                touch "$PIP_MARKER"
                _e "     Libraries ready"
            else
                _e "     Some libraries could not be installed"
                echo ""
                _e "----- Install log (last 20 lines) -----"
                tail -n 20 "$PIP_LOG" 2>/dev/null
                echo ""
            fi
        fi
    fi

    echo ""
    echo "==========================================================="
    _e "   Setup complete!"
    _e "   You don't need to do anything else. Just run this file again to start."
    echo "==========================================================="
    echo ""
}

run_tool() {
    if [ ! -f "$APP/1_light_android.py" ]; then
        _e "File 1_light_android.py not found in Download"
        _e "Please copy it to $APP"
        return 1
    fi
    _e "(Starting in a few seconds...) ... Running tool"
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-$PREFIX/tmp}"
    mkdir -p "$XDG_RUNTIME_DIR" 2>/dev/null
    start_pulse
    unset LD_PRELOAD
    unset ANDROID_PINNED_TOOLS
    sleep 1
    PA_BIND=""
    if [ -n "${PA_SOCKET:-}" ] && [ -S "$PA_SOCKET" ]; then
        PA_BIND="-b $PA_SOCKET:/tmp/pulse/native"
        if [ "${PA_MODE:-}" = "real" ]; then
            _e "     PulseAudio: Android audio (real mic + speaker)"
        else
            _e "     PulseAudio: connected (virtual devices)"
        fi
    else
        _e "     PulseAudio: not available (no audio I/O)"
    fi
    exec "$PREFIX/bin/proot" -0 \
        -r "$DEST" \
        -b /proc -b /dev -b /sys \
        -b /system:/system \
        -b /vendor:/vendor \
        -b /apex:/apex \
        -b /sdcard:/sdcard \
        $PA_BIND \
        -w "$APP" \
        /usr/bin/env PULSE_SERVER=unix:/tmp/pulse/native LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu:/usr/lib \
        /usr/bin/python3.11 1_light_android.py
}

banner
if setup_all; then
    run_tool
fi
