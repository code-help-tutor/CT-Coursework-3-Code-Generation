WeChat: cstutorcs
QQ: 749389476
Email: tutorcs@163.com
#!/usr/bin/env python3

import argparse
import subprocess


def update_file(filename: str):

    f = open(filename)

    run = ""
    input = ""
    comment_char = ""

    lines = f.readlines()
    if lines[0].startswith('#'):
        comment_char = '#'
    elif lines[0].startswith('//'):
        comment_char = '//'
    assert comment_char != ""

    comment_block_over = False

    for l in lines:
        if l.startswith(f'{comment_char} RUN:'):
            start_idx = l.find("RUN:") + 4  # skip RUN:
            end_idx = l.find("%s | filecheck")
            run += l[start_idx:end_idx].strip()
        else:
            if l.startswith(f'{comment_char} XFAIL') or l.startswith(
                    f'{comment_char} CHECK'):
                continue  # always remove XFAIL and CHECK/CHECK-NEXT lines
            elif l.startswith(comment_char) and not comment_block_over:
                input += l  # add initial block of comments after RUN
            elif l == "\n" or l.strip() == "":
                input += l  # always preserve line breaks and empty lines
            elif not l.startswith(comment_char):
                comment_block_over = True  # after we find a non-comment line discard comments
                input += l

    f.close
    new_run = ""
    old_run = run.split(" ")
    if old_run[0] == "choco-opt":
        new_run = "choco_opt.py" + " " + " ".join(old_run[1:])
        print(new_run)
    elif old_run[0] == "choco-lexer":
        new_run = "choco_lexer.py" + " " + " ".join(old_run[1:])
        print(new_run)
    elif old_run[0] == "riscv-interpreter":
        new_run = "riscv_interpreter.py" + " " + " ".join(old_run[1:])
        print(new_run)
    elif old_run[0] == "riscv-lexer":
        new_run = "riscv_lexer.py" + " " + " ".join(old_run[1:])
        print(new_run)
    else:
        print("wrong run command: ", run)
        exit(1)
    raw_output = subprocess.Popen(f"{run} {args.file}",
                                  shell=True,
                                  stdout=subprocess.PIPE).stdout
    assert raw_output
    output = raw_output.read().decode('ascii').strip()

    output = output.replace("\n", f"\n{comment_char} CHECK-NEXT: ")
    output = f"{comment_char} CHECK:      " + output

    new_file_content = f"{comment_char} RUN: {run} %s | filecheck %s"
    new_file_content += "\n\n"
    new_file_content += input.strip()
    new_file_content += "\n\n"
    new_file_content += output
    new_file_content += "\n"

    f = open(filename, "w+")
    f.write(new_file_content)
    f.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    args = parser.parse_args()
    update_file(args.file)
