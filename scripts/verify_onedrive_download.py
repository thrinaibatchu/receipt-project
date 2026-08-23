import hashlib

from receipt_project.onedrive import (
    download_drive_item,
    list_receipt_files,
)


def main():
    files = list_receipt_files()

    print(f"Receipt candidates found: {len(files)}")

    if not files:
        print("Nothing to download.")
        return

    for item in files:
        filename = item["name"]
        item_id = item["id"]
        expected_size = item.get("size")

        print()
        print(f"Downloading: {filename}")

        content = download_drive_item(item_id)

        actual_size = len(content)
        sha256 = hashlib.sha256(content).hexdigest()

        if expected_size is not None and actual_size != expected_size:
            raise RuntimeError(
                f"Size mismatch for {filename}: "
                f"Graph reported {expected_size}, "
                f"downloaded {actual_size}"
            )

        print("Download: SUCCESS")
        print(f"Bytes downloaded: {actual_size}")
        print("Graph size verification: SUCCESS")
        print(f"SHA-256: {sha256}")


if __name__ == "__main__":
    main()
