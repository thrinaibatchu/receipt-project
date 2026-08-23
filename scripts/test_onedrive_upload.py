from receipt_project.onedrive import (
    download_from_receipts,
    upload_to_receipts,
)


TEST_FILENAME = "_graph_smoke_test.txt"

TEST_CONTENT = (
    b"Receipt Project Microsoft Graph upload test.\n"
)


def main():
    print(f"Uploading: {TEST_FILENAME}")

    uploaded = upload_to_receipts(
        filename=TEST_FILENAME,
        content=TEST_CONTENT,
        content_type="text/plain",
    )

    print("OneDrive upload: SUCCESS")
    print(
        "File ID returned:",
        "YES" if uploaded.get("id") else "NO",
    )

    downloaded = download_from_receipts(TEST_FILENAME)

    if downloaded != TEST_CONTENT:
        raise RuntimeError(
            "Downloaded file does not match uploaded content."
        )

    print("OneDrive download: SUCCESS")
    print("Content verification: SUCCESS")


if __name__ == "__main__":
    main()
