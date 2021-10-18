import argparse
import subprocess
from termcolor import cprint
from typing import Optional, IO
import os
from progress.spinner import PixelSpinner
import time
import re
from datetime import datetime
import shutil
import glob
import tempfile

EXIT_CODE_SUCCESS = 0
EXIT_CODE_STUDENT_CODE_ERROR = 1
EXIT_CODE_AUTOGRADER_FAILURE = 255

PASS_ICON = "Passed: "
FAIL_ICON = "Failed: "
MEM_ICON = "Memory or register issue: "
FAIL_MEM_ICON = "Failed and has memory or register issue: "

detail_report = False
total_print_decimal = 51
total_strlen = 21
# also remember to change total scores, search 6

spec_issue_count = 4
spec_issue_list = [
    "WARN_POSSIBLE_WILD_READ",
    "WARN_READ_UNINITIALIZED_MEMORY",
    "WARN_WRITE_UNINITIALIZED_MEMORY",
    "ERR_REGISTER_CHANGED"
]


def get_issue_list() -> [str]:
    """
    Get the list of detectable issues from the klc3 header.
    :return: list of issue names in str
    """
    with open("Issue.h", "r") as f:
        buf = f.read()
    res = re.search(r"enum Type \{(.+?)\};", buf, re.MULTILINE | re.DOTALL)
    issues = res.group(1).replace("\n", "").replace(" ", "").split(",")
    issues.remove("NO_ISSUE")
    issues.remove("")
    return issues


def remove_extension(filename: str) -> str:
    return os.path.splitext(filename)[0]


# I will rewrite this shit if I have time
def run_subroutine_test(test_subroutine: str, student_filename: str, input_data_list: [str], is_regression: bool,
                        output_dir: str, temp_dir: str) -> int:

    # preprocess
    if test_subroutine == 'print_decimal':
        subprocess.run(["cp", "print_decimal/entry.asm", "mp1_print_decimal.asm"])
        with open("mp1_print_decimal.asm", 'a') as outfile:
            subprocess.run(["sed", "-e", '/\.ORIG/d', "-e", '/\.END/d', student_filename], stdout=outfile)
        with open("mp1_print_decimal.asm", 'a') as outfile:
            subprocess.run(["printf", "\n.END\n"], stdout=outfile)
    elif test_subroutine == 'strlen':
        subprocess.run(["cp", "strlen/entry.asm", "mp1_strlen.asm"])
        with open("mp1_strlen.asm", 'a') as outfile:
            subprocess.run(["sed", "-e", '/\.ORIG/d', "-e", '/\.END/d', student_filename], stdout=outfile)
        with open("mp1_strlen.asm", 'a') as outfile:
            subprocess.run(["printf", "\n.END\n"], stdout=outfile)

    # call klc3
    if test_subroutine == 'strlen':
        klc3_command = [
            "klc3",
            "--use-forked-solver=false",
            "--max-lc3-step-count=50000",
            "--max-lc3-out-length=50",
            "--output-dir=%s" % output_dir,
            "assertions_.asm",
            input_data_list[0]+".asm",
            "--test", "mp1_strlen.asm",
            "--gold", "strlen/gold_strlen.asm"
        ]
    elif test_subroutine == 'print_decimal':
        klc3_command = [
            "klc3",
            "--use-forked-solver=false",
            "--max-lc3-step-count=50000",
            "--max-lc3-out-length=50",
            "--output-dir=%s" % output_dir,
            "assertions_.asm",
            input_data_list[0]+".asm",
            "--test", "mp1_print_decimal.asm",
            "--gold", "print_decimal/gold_print_decimal.asm"
        ]
    proc = subprocess.Popen(klc3_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with open(os.path.join(output_dir, "klc3.log"), "w") as log_file:
        log_file.write("$ %s\n\n" % "\n".join(klc3_command))
        while proc.poll() is None:
            line = proc.stdout.readline()
            log_file.write(line.decode())
    exit_code = proc.wait()
    if exit_code != 0:
        cprint("klc3 terminated abnormally", "red")
        exit(EXIT_CODE_AUTOGRADER_FAILURE)

    # clean up
    subprocess.run(['sh', 'clean.sh'])

    return EXIT_CODE_SUCCESS


def run_subroutine_test_old(test_subroutine: str, student_filename: str, input_data_list: [str], is_regression: bool,
                        output_dir: str, temp_dir: str) -> int:
    """
    Run regression/symbolic test of one subroutine on the student code
    :param test_subroutine:
    :param student_filename: need to be parsed already
    :param input_data_list:
    :param is_regression:
    :param output_dir:
    :param temp_dir:
    :return: 0 for success (may or may not have issues), 1 for student code error. Exit with 255 for workflow failure.
    """

    # Read sym file of student code to get subroutine addr
    print(test_subroutine, student_filename, input_data_list, output_dir, temp_dir)
    test_subroutine_addr = -1
    targeting_prefix = "//	" + test_subroutine.upper() + " "
    for line in open(remove_extension(student_filename) + ".sym", "r"):
        if line.startswith(targeting_prefix):
            test_subroutine_addr = int(line[len(targeting_prefix):].strip(), 16)
            break
    if test_subroutine_addr == -1:
        with open(os.path.join(output_dir, "report.md"), "w") as report_file:
            report_file.write(FAIL_ICON + " Failed to find subroutine %s in your code." % test_subroutine.upper())
        return EXIT_CODE_STUDENT_CODE_ERROR

    # Generate entry asm
    entry_filename = "entry.asm"
    entry_content = open(os.path.join(test_subroutine, entry_filename), "r").read()
    entry_content = entry_content.replace("{{%s}}" % test_subroutine.upper(),
                                          "x%04X" % (test_subroutine_addr - (0x2FF0 + 2)))
    temp_entry_filename = os.path.join(temp_dir, entry_filename)
    open(temp_entry_filename, "w").write(entry_content)

    # Compile temp entry file
    proc = subprocess.Popen(["klc3-parser", temp_entry_filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with open(os.path.join(output_dir, "klc3-parser-entry.log"), "w") as log_file:
        while proc.poll() is None:
            line = proc.stdout.readline()
            log_file.write(line.decode())
            # spinner.next()
    exit_code = proc.wait()
    if exit_code != 0:
        cprint("klc3-parser on entry code terminated abnormally", "red")
        exit(EXIT_CODE_AUTOGRADER_FAILURE)

    # Run klc3
    klc3_command = [
        "klc3",
        "--use-forked-solver=false",
        "--report-to-terminal",
        "--output-dir=%s" % output_dir,
        "--report-relative-path=%s/" % test_subroutine,
        # MP1 options
        "--max-lc3-step-count=50000",
        "--max-lc3-out-length=50"]

    if is_regression:
        klc3_command.append("--output-for-replay=false")
        klc3_command.append("--output-flowgraph=false")
    else:
        klc3_command.append("--output-flowgraph")

    # Always load the register assertion file
    # klc3_command.append("register_assert_")
    input_data_list[0] = input_data_list[0] + '.asm'
    klc3_command += input_data_list
    klc3_command += [
        # Test programs
        "--test", student_filename,
        "--test", temp_entry_filename,
        # Gold program
        "--gold", os.path.join(test_subroutine, "gold.asm"),
    ]

    proc = subprocess.Popen(klc3_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with open(os.path.join(output_dir, "klc3.log"), "w") as log_file:
        log_file.write("$ %s\n\n" % "\n".join(klc3_command))
        while proc.poll() is None:
            line = proc.stdout.readline()
            log_file.write(line.decode())
    exit_code = proc.wait()
    if exit_code != 0:
        cprint("klc3 terminated abnormally", "red")
        exit(EXIT_CODE_AUTOGRADER_FAILURE)

    return EXIT_CODE_SUCCESS


def enum_input_data_list(case_dir: str) -> [str]:
    ret = []
    input_list = glob.glob(os.path.join(case_dir, "*.asm"))
    for input_data_file in input_list:
        basename = remove_extension(input_data_file)
        ret.append(basename)
        if not os.path.exists(basename + ".info"):  # if already parsed, skip, since regression asm will not be changed
            proc = subprocess.Popen(["klc3-parser", input_data_file],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            exit_code = proc.wait()
            if exit_code != 0:
                cprint("Error parsing regression input file %s" % input_data_file, "red")
                exit(EXIT_CODE_AUTOGRADER_FAILURE)
    return ret


def run_all_regression(student_filename: str, regression_dir: str, subroutine_list: [str],
                       root_output_dir: str, root_temp_dir: str, root_store_dir: str) -> (str, int, int, int, int):
    """
    Run all regression test. regression_dir has the structure of commit_id/subroutine-test******.
    :param student_filename:
    :param regression_dir:
    :param subroutine_list:
    :param root_output_dir:
    :param root_temp_dir:
    :param root_store_dir:
    :return: (all pass, output)
    """

    # Create dirs
    regression_store_dir = os.path.join(root_store_dir, "regression")
    os.makedirs(regression_store_dir, exist_ok=True)
    regression_temp_dir = os.path.join(root_temp_dir, "regression")
    os.makedirs(regression_temp_dir, exist_ok=True)
    regression_copy_dir = os.path.join(root_output_dir, "regression")
    os.makedirs(regression_copy_dir, exist_ok=True)

    ret_report = ""
    ret_print_decimal = 0
    ret_strlen = 0
    ret_print_decimal_issue = 0
    ret_strlen_issue = 0

    # Enumerate commits in regression dir
    for commit_path in glob.glob(os.path.join(regression_dir, "*")):
        commit_id = os.path.basename(commit_path)

        for case_dir in glob.glob(os.path.join(commit_path, "*")):
            case_name = os.path.basename(case_dir)
            p = case_name.split("-")
            if p[0] == 'print':
                p = [p[0]+'_'+p[1], p[2]]
            if len(p) > 1 and p[0] in subroutine_list:
                # Is a regression test directory
                combined_name = commit_id + "-" + case_name

                # Copy to output
                case_copy_dir = os.path.join(regression_copy_dir, combined_name)
                os.makedirs(case_copy_dir, exist_ok=True)
                for case_asm in glob.glob(os.path.join(case_dir, "*.asm")):
                    shutil.copy(case_asm, case_copy_dir)

                # Output to store
                case_output_dir = os.path.join(regression_store_dir, combined_name)
                os.makedirs(case_output_dir, exist_ok=True)
                case_temp_dir = os.path.join(regression_temp_dir, combined_name)
                os.makedirs(case_temp_dir, exist_ok=True)

                return_code = run_subroutine_test(
                    test_subroutine=p[0],
                    student_filename=student_filename,
                    input_data_list=enum_input_data_list(case_dir),
                    is_regression=True,
                    output_dir=case_output_dir,
                    temp_dir=case_temp_dir,
                )
                # No matter the return code is 0 or 1, report.md is always generated

                if return_code == EXIT_CODE_STUDENT_CODE_ERROR:
                    if commit_id == "strlen":
                        ret_strlen_issue = -1
                    else:
                        ret_print_decimal_issue = -1
                    continue
                elif return_code == EXIT_CODE_AUTOGRADER_FAILURE:
                    cprint("AUTOGRADER FAIL!", "red")

                case_name_and_link = case_name
                case_report = open(os.path.join(case_output_dir, "report.md"), "r").read()
                if case_report == "":
                    # No issue
                    if detail_report:
                        ret_report += PASS_ICON + case_name + '\n'

                    if commit_id == "strlen":
                        ret_strlen += 1
                    else:
                        ret_print_decimal += 1

                else:
                    # Check whether there are issue other than incorrect answer
                    issues = []
                    log = open(os.path.join(case_output_dir, "klc3.log"), "r")
                    for line in log.readlines():
                        if line.startswith("ERR_") or line.startswith("WARN_"):
                            issues.append(line[:-1].split(' ')[0])
                    log.close()

                    wrong = False
                    for issue in issues:
                        if issue.startswith("ERR_") and (not issue.startswith("ERR_REGISTER_CHANGED")):
                            wrong = True
                            # if issue.startswith("ERR_STATE_"):  # didn't finished
                            #     if commit_id == "strlen":
                            #         ret_strlen_issue += spec_issue_count
                            #     else:
                            #         ret_print_decimal_issue += spec_issue_count
                            continue
                        elif issue in spec_issue_list:
                            if commit_id == "strlen":
                                ret_strlen_issue += 1
                            else:
                                ret_print_decimal_issue += 1

                    if not wrong:
                        if commit_id == "strlen":
                            ret_strlen += 1
                        else:
                            ret_print_decimal += 1

                    if detail_report:
                        ret_report += case_name + '\n' \
                                      + case_report + '\n\n'
                    else:
                        if not wrong:
                            ret_report += MEM_ICON + case_name + '\n'
                        elif len(issues) == 1:
                            ret_report += FAIL_ICON + case_name + '\n'
                        else:
                            ret_report += FAIL_MEM_ICON + case_name + '\n'

    if ret_report == "" and ret_strlen_issue != -1 and ret_print_decimal_issue != -1:
        ret_report = "All tests passed"
        ret_report = '\n' + ret_report + '\n'
    if ret_strlen_issue == -1:
        ret_report += "Fail to find strlen in your code\n"
    if ret_print_decimal_issue == -1:
        ret_report += "Fail to find print_decimal in your code\n"
    return ret_report, ret_print_decimal, ret_strlen, ret_print_decimal_issue, ret_strlen_issue


def generate_grade(regression_report: str, report: str, output_dir: str) -> None:
    content = open("templates/klc3_report.md", "r").read()
    content = content.replace("{{REGRESSION_REPORT}}", regression_report)
    content = content.replace("{{REPORT}}", report)
    open(os.path.join(output_dir, "grade.md"), "w").write(content)


def parse_student_code(student_filename: str, output_dir: str) -> str:
    proc = subprocess.Popen(["klc3-parser", student_filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with open(os.path.join(output_dir, "klc3-parser-student.log"), "w") as log_file:
        while proc.poll() is None:
            line = proc.stdout.readline()
            log_file.write(line.decode())
    exit_code = proc.wait()
    if exit_code != 0:
        cprint("klc3-parser on student code terminated abnormally", "red")
        return FAIL_ICON + " Your code failed to compile.\n" \
               + "\n" \
               + "lc3as output:\n" \
               + "```\n" \
               + open(os.path.join(output_dir, "klc3-parser-student.log"), "r").read() \
               + "\n```"

    return ""


def run_mp1_test(test_asm: str, regression_dir: str, output_dir: str, subroutine_list: [str]) -> int:
    # Create root output dir
    os.makedirs(output_dir, exist_ok=True)
    # Create root store dir
    store_dir = os.path.join(output_dir, "store")
    os.makedirs(store_dir, exist_ok=True)

    # Create root temp dir
    temp_dir = tempfile.mkdtemp()

    # Copy gitignore
    shutil.copy("templates/.gitignore", output_dir)

    # Copy student code to temp dir
    test_basename = os.path.basename(test_asm)
    temp_student_filename = os.path.join(temp_dir, test_basename)
    shutil.copy(test_asm, temp_student_filename)

    # Parse student code
    parse_report = parse_student_code(temp_student_filename, store_dir)
    if parse_report != "":
        generate_grade(FAIL_ICON + " Your code failed to compile.", "\nFunctionality score: 0/65", output_dir)
        os.system("rm -rf " + temp_dir)
        return EXIT_CODE_SUCCESS

    # Run regression tests
    regression_report, passed_print_decimal, passed_strlen, print_decimal_issue, strlen_issue = run_all_regression(
        student_filename=temp_student_filename,
        regression_dir=regression_dir,
        subroutine_list=subroutine_list,
        root_output_dir=output_dir,
        root_temp_dir=temp_dir,
        root_store_dir=store_dir
    )

    grade_message = "strlen passed: " + str(passed_strlen) + '/' + str(total_strlen) + '\n' + \
                    "print_decimal passed: " + str(passed_print_decimal) + '/' + str(total_print_decimal) + "\n"

    funtionality_score = passed_strlen*10/total_strlen + passed_print_decimal*40/total_print_decimal

    if strlen_issue != -1:
        grade_message += "Total strlen memory or register issue: " + str(strlen_issue) + "\n"
        funtionality_score += (1 - strlen_issue / (total_strlen * spec_issue_count)) * 5

    if print_decimal_issue != -1:
        grade_message += "Total print_decimal memory or register issue: " + str(print_decimal_issue) + "\n"
        funtionality_score += (1 - print_decimal_issue / (total_print_decimal * spec_issue_count)) * 10

    funtionality_score = int(funtionality_score + 0.5)

    grade_message += "\nFunctionality score: " + str(funtionality_score) + '/' + "65\n"

    generate_grade(regression_report, grade_message, output_dir)
    os.system("rm -rf " + temp_dir)
    return EXIT_CODE_SUCCESS


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--regression-dir", help="Regression directory", dest="regression_dir")
    parser.add_argument("--output-dir", help="Output directory, should not be .", dest="output_dir")
    parser.add_argument("file", help="Student asm file (*.asm)")
    argv = parser.parse_args()

    subroutines = ["strlen", "print_decimal"]

    exit(run_mp1_test(
        test_asm=argv.file,
        regression_dir=argv.regression_dir,
        output_dir=argv.output_dir,
        subroutine_list=subroutines,
    ))