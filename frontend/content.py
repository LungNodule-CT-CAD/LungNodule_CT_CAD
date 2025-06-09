import os

def crawl_directory(path, output_file, indent=0):
    with open(output_file, 'a', encoding='utf-8') as f:
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            relative_path = os.path.relpath(item_path, ".")
            indent_str = "  " * indent
            if item == 'node_modules':
                f.write(f"{indent_str}{relative_path}/: [Dependency folder, not crawled]\n\n")
                continue
            if item == 'package-lock.json' and path == ".":
                f.write(f"{indent_str}{relative_path}: [Lock file, not crawled]\n\n")
                continue
            if os.path.isfile(item_path):
                f.write(f"{indent_str}{relative_path}:\n")
                try:
                    with open(item_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        f.write(f"{indent_str}{content}\n\n")
                except:
                    f.write(f"{indent_str}[Binary or unreadable file]\n\n")
            elif os.path.isdir(item_path):
                f.write(f"{indent_str}{relative_path}/:\n")
                crawl_directory(item_path, output_file, indent + 1)

if __name__ == "__main__":
    output_file = "nodes.txt"
    open(output_file, 'w').close()  # Clear file
    crawl_directory(".", output_file)