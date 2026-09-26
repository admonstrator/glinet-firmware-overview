#!/bin/sh
# GL.iNet Firmware Overview - interactive terminal menu
#
#   curl -s __SITE_URL__/cli | sh        any POSIX sh, including BusyBox ash on OpenWrt
#   wget -qO- __SITE_URL__/cli | sh      routers without curl
#   sh <(curl -s __SITE_URL__/cli)       bash / zsh
#
# Needs only a POSIX shell with awk, sed and cut (BusyBox is enough) plus one of
# curl, wget or uclient-fetch. Menu input is read from /dev/tty, so the script
# also works when piped into sh. Data comes from the flat-file API: __SITE_URL__/api/

SITE="__SITE_URL__"
UA="glinet-firmware-cli"
TTY=/dev/tty
[ -r "$TTY" ] || TTY=/dev/stdin

TMP=$(mktemp -d 2>/dev/null || mktemp -d -t glinet)
trap 'rm -rf "$TMP"' EXIT
trap 'exit 130' INT TERM

if command -v curl >/dev/null 2>&1; then
    fetch() { curl -fsSL -A "$UA" "$SITE/$1"; }
    download() { curl -fL --progress-bar -A "$UA" -o "$2" "$1"; }
elif command -v wget >/dev/null 2>&1; then
    fetch() { wget -q -O - -U "$UA" "$SITE/$1"; }
    download() { wget -O "$2" -U "$UA" "$1"; }
elif command -v uclient-fetch >/dev/null 2>&1; then
    fetch() { uclient-fetch -q -O - -U "$UA" "$SITE/$1"; }
    download() { uclient-fetch -O "$2" -U "$UA" "$1"; }
else
    echo "This menu needs curl, wget or uclient-fetch." >&2
    exit 1
fi

if [ -z "$PAGER" ]; then
    if command -v less >/dev/null 2>&1; then PAGER=less
    elif command -v more >/dev/null 2>&1; then PAGER=more
    else PAGER=cat; fi
fi

# ANSI colours only on a terminal; tput is not available on BusyBox
if [ -t 1 ] && [ "${TERM:-dumb}" != dumb ]; then
    B=$(printf '\033[1m'); D=$(printf '\033[2m'); G=$(printf '\033[32m'); Y=$(printf '\033[33m'); C=$(printf '\033[36m'); R=$(printf '\033[0m')
else
    B=; D=; G=; Y=; C=; R=
fi

field() { printf '%s\n' "$row" | cut -f"$1"; }

ask() {
    printf '%s' "$1"
    IFS= read -r REPLY <"$TTY" || REPLY=q
}

header() {
    printf '\n%s%s%s\n' "$B" "$1" "$R"
    printf '%s%s%s\n' "$D" "$(printf '%s' "$1" | sed 's/./=/g')" "$R"
}

# --- data ------------------------------------------------------------------

fetch api/models >"$TMP/models" 2>/dev/null || { echo "Could not reach $SITE/api/models" >&2; exit 1; }
MODEL_COUNT=$(wc -l <"$TMP/models" | tr -d ' ')

count_type() { awk -F'\t' -v t="$1" '$2 == t' "$TMP/models" | wc -l | tr -d ' '; }

# list_models TYPE QUERY -> writes the matching rows to $TMP/list and prints them numbered
list_models() {
    awk -F'\t' -v t="$1" -v q="$(printf '%s' "$2" | tr 'A-Z' 'a-z')" \
        '(t == "" || $2 == t) && (q == "" || index(tolower($1 "\t" $3), q))' "$TMP/models" >"$TMP/list"
    awk -F'\t' -v b="$B" -v r="$R" -v g="$G" -v d="$D" \
        '{ printf "  %s%2d%s  %-12s %-34s %s%s%s\n", b, NR, r, $1, $3, g, $4, r }' "$TMP/list"
    [ -s "$TMP/list" ]
}

# --- stage menu ------------------------------------------------------------

stage_menu() { # CODE NAME STAGE VERSION URL MD5 LINK FALLBACK_VERSION FALLBACK_URL
    code=$1; name=$2; stage=$3; version=$4; url=$5; md5=$6; link=$7; fbv=$8; fbu=$9
    while :; do
        header "$name - $stage $version"
        printf '  Download   %s\n' "$url"
        [ -n "$md5" ] && printf '  MD5        %s\n' "$md5"
        if [ "$link" != "ok" ]; then
            printf '  %sLink check %s in the last build; the version stays listed.%s\n' "$Y" "$link" "$R"
            [ -n "$fbu" ] && printf '  Newest reachable build: %s %s\n' "$fbv" "$fbu"
        fi
        printf '\n  %s1%s changelog   %s2%s download to %s   %s3%s print URL   %sb%s back   %sq%s quit\n' \
            "$B" "$R" "$B" "$R" "$(pwd)" "$B" "$R" "$B" "$R" "$B" "$R"
        ask "> "
        case $REPLY in
            1)  if [ -t 1 ]; then fetch "api/$code/$stage/changelog" | $PAGER; else fetch "api/$code/$stage/changelog"; fi ;;
            2)  dl_url=$url
                if [ "$link" != "ok" ] && [ -n "$fbu" ]; then
                    ask "  The $version download did not respond in the last build. Fetch $fbv instead? [y/N] "
                    case $REPLY in y|Y) dl_url=$fbu ;; esac
                fi
                file=${dl_url##*/}
                printf '  %s-> %s%s\n' "$D" "$file" "$R"
                if download "$dl_url" "$file"; then
                    printf '  %sSaved %s%s\n' "$G" "$file" "$R"
                    if [ -n "$md5" ] && [ "$dl_url" = "$url" ]; then
                        if command -v md5sum >/dev/null 2>&1; then sum=$(md5sum "$file" | cut -d' ' -f1)
                        elif command -v md5 >/dev/null 2>&1; then sum=$(md5 -q "$file")
                        else sum=; fi
                        [ -n "$sum" ] && { [ "$sum" = "$md5" ] && printf '  %sMD5 ok%s\n' "$G" "$R" || printf '  %sMD5 MISMATCH: %s%s\n' "$Y" "$sum" "$R"; }
                    fi
                else
                    printf '  %sDownload failed%s\n' "$Y" "$R"
                fi ;;
            3)  printf '%s\n' "$url" ;;
            b|B|"") return ;;
            q|Q) exit 0 ;;
        esac
    done
}

# --- device menu -----------------------------------------------------------

device_menu() { # CODE NAME
    code=$1; name=$2
    fetch "api/$code/stages" >"$TMP/stages" 2>/dev/null || { printf '  %sNo data for %s%s\n' "$Y" "$code" "$R"; return; }
    while :; do
        header "$name ($code)"
        if [ ! -s "$TMP/stages" ]; then
            echo "  No verified firmware download is currently available for this model."
        else
            awk -F'\t' -v b="$B" -v r="$R" -v y="$Y" -v d="$D" \
                '{ flag = ($6 == "ok") ? "" : y " (link " $6 ")" r
                   printf "  %s%2d%s  %-12s %-9s %s%s%s%s\n", b, NR, r, $1, $2, d, substr($3, 1, 10), r, flag }' "$TMP/stages"
        fi
        printf '\n  %sweb%s %s/%s/   %sb%s back   %sq%s quit\n' "$D" "$R" "$SITE" "$code" "$B" "$R" "$B" "$R"
        ask "> "
        case $REPLY in
            b|B|"") return ;;
            q|Q) exit 0 ;;
            *[!0-9]*) ;;
            *)  row=$(sed -n "${REPLY}p" "$TMP/stages")
                [ -z "$row" ] && continue
                # cut keeps empty fields, unlike read with a tab IFS
                stage_menu "$code" "$name" "$(field 1)" "$(field 2)" "$(field 4)" "$(field 5)" "$(field 6)" "$(field 7)" "$(field 8)" ;;
        esac
    done
}

# --- model list ------------------------------------------------------------

model_list() { # TYPE TITLE [QUERY]
    while :; do
        header "$2"
        if ! list_models "$1" "$3"; then
            echo "  Nothing matches '$3'."
            return
        fi
        printf '\n  number = open   %sb%s back   %sq%s quit\n' "$B" "$R" "$B" "$R"
        ask "> "
        case $REPLY in
            b|B|"") return ;;
            q|Q) exit 0 ;;
            *[!0-9]*) ;;
            *)  row=$(sed -n "${REPLY}p" "$TMP/list")
                [ -z "$row" ] && continue
                device_menu "$(field 1)" "$(field 3)" ;;
        esac
    done
}

# --- recently released -----------------------------------------------------

recent() { # the /new text page: recently released builds, newest first
    if fetch new/index.txt >"$TMP/new" 2>/dev/null && [ -s "$TMP/new" ]; then
        if [ -t 1 ]; then $PAGER "$TMP/new"; else cat "$TMP/new"; fi
    else
        printf '  %sCould not load %s/new%s\n' "$Y" "$SITE" "$R"
    fi
}

# --- main menu -------------------------------------------------------------

while :; do
    header "GL.iNet Firmware Overview  ($MODEL_COUNT models)"
    printf '  %s1%s  Routers      %s\n' "$B" "$R" "$(count_type ROUTER)"
    printf '  %s2%s  IoT devices  %s\n' "$B" "$R" "$(count_type IOT)"
    printf '  %s3%s  KVM / Comet  %s\n' "$B" "$R" "$(count_type KVM)"
    printf '  %s4%s  Recently released\n' "$B" "$R"
    printf '\n  Or type a model code or a search term (e.g. %smt3000%s, %sflint%s).   %sq%s quit\n' "$C" "$R" "$C" "$R" "$B" "$R"
    ask "> "
    case $REPLY in
        1) model_list ROUTER "Routers" ;;
        2) model_list IOT "IoT devices" ;;
        3) model_list KVM "KVM / Comet" ;;
        4) recent ;;
        q|Q) exit 0 ;;
        "") ;;
        *)  q=$(printf '%s' "$REPLY" | tr 'A-Z' 'a-z')
            row=$(awk -F'\t' -v c="$q" 'tolower($1) == c' "$TMP/models")
            if [ -n "$row" ]; then
                device_menu "$(field 1)" "$(field 3)"
            else
                model_list "" "Search: $REPLY" "$q"
            fi ;;
    esac
done
