#!/bin/sh

set -eu

ios_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
failed=0

for file in "$ios_root"/CrediWise/Resources/*.lproj/*.strings; do
    while IFS= read -r line || [ -n "$line" ]; do
        normalized=$(printf '%s' "$line" | tr '[:upper:]' '[:lower:]')

        case "$normalized" in
            *"guaranteed approval"*|*"banks will approve"*|*"credit score recognized by banks"*|\
                *"persetujuan dijamin"*|*"bank akan menyetujui"*|*"skor kredit yang diakui bank"*)
                printf '%s\n' "Prohibited positioning claim in $file: $line" >&2
                failed=1
                ;;
        esac

        case "$normalized" in
            *"official credit score"*)
                case "$normalized" in
                    *"not an official credit score"*) ;;
                    *)
                        printf '%s\n' "Prohibited positioning claim in $file: $line" >&2
                        failed=1
                        ;;
                esac
                ;;
        esac

        case "$normalized" in
            *"skor kredit resmi"*)
                case "$normalized" in
                    *"bukan skor kredit resmi"*) ;;
                    *)
                        printf '%s\n' "Prohibited positioning claim in $file: $line" >&2
                        failed=1
                        ;;
                esac
                ;;
        esac
    done < "$file"
done

exit "$failed"
