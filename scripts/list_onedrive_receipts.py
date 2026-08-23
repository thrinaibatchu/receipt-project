from receipt_project.onedrive import list_receipt_files


def main():
    files = list_receipt_files()

    print(f"Receipt candidates found: {len(files)}")

    for item in files:
        print(
            f"- {item['name']} "
            f"({item.get('size', 0)} bytes)"
        )


if __name__ == "__main__":
    main()
