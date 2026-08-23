from receipt_project.onedrive import ensure_receipts_folder


def main():
    folder = ensure_receipts_folder()

    print("Refresh-token authentication: SUCCESS")
    print("OneDrive /Receipts landing zone: SUCCESS")
    print(
        "Folder ID returned:",
        "YES" if folder.get("id") else "NO",
    )


if __name__ == "__main__":
    main()
