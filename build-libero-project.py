# The BeagleV Fire Bitstream Builder is released under the following software license:

#  Copyright 2021 Microchip Corporation.
#  SPDX-License-Identifier: MIT


#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:

#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.

#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
#  IN THE SOFTWARE.


# The BeagleV Fire Bitstream Builder is an evolution of the Microchip
# Bitstream Builder available from:
# https://github.com/polarfire-soc/icicle-kit-minimal-bring-up-design-bitstream-builder
# 



import argparse
import os
import re
import shutil
import yaml
import sys


class CustomSource:
  def __init__(self, new_cape_name, template_name, project_path, script_args):
    self.new_cape_name = new_cape_name
    self.template_name = template_name
    self.project_path = project_path
    self.script_args = script_args


# Parse command line arguments and set tool locations
def parse_arguments():
    global libero
    global yaml_input_file
    global force_delete

    # Initialize parser
    parser = argparse.ArgumentParser()

    parser.add_argument("-f", "--force", help="Force delete existing custom cape if present",
                    action="store_true")
    parser.add_argument('Path',
                       metavar='path',
                       type=str,
                       help='Path to the YAML file describing the list of sources used to build the bitstream.')

    # Read arguments from command line
    args = parser.parse_args()
    if args.force:
        force_delete = args.force
    yaml_input_file_arg = args.Path

    if not os.path.isfile(yaml_input_file_arg):
        print("\r\n!!! The path specified for the YAML input file does not exist !!!\r\n")
        parser.print_help()
        sys.exit()

    yaml_input_file = os.path.abspath(yaml_input_file_arg)
    libero = "libero"



def validate_input(source_list):
    global gateware_repo_path
    global cape_dir_path
    global new_project_path

    # Check current working directory and expected structure
    folder_name = os.path.split(os.getcwd())[1]
    git_file = os.path.join(os.getcwd(), ".git")
    if not (folder_name == "gateware" and os.path.exists(git_file)):
        print("This script is expected to run at the top level of the \"gateware\" repository.")
        exit()

    gateware_repo_path = os.getcwd()
    expected_cape_subdirectory = "sources/FPGA-design/script_support/components/CAPE"
    cape_dir_path = os.path.join(gateware_repo_path, expected_cape_subdirectory)
    if not(os.path.exists(gateware_repo_path) and os.path.exists(cape_dir_path)):
        print("This script expects capes to be stored at {}".format(expected_cape_subdirectory))
        exit()

    with open(source_list) as f:  # open the yaml file passed as an arg
        data = yaml.load(f, Loader=yaml.FullLoader)

        keys = data.keys()
        fpga_key = ""
        for source in keys:
            if "custom-source" in data.get(source).get("type"):
                fpga_key = source
                break

        template_cape_name = data.get(fpga_key).get("cape-template")
        new_cape_name = data.get(fpga_key).get("cape-name")
        existing_cape_names = ["DEFAULT", "GPIOS", "NONE", "NONE_NO_USER_LEDS", "ROBOTICS", "VERILOG_TEMPLATE", "VERILOG_TUTORIAL"]
        # Verify we aren't messing with the existing capes
        if new_cape_name in existing_cape_names:
            print("New cape name cannot be the same as a built in cape name")
            exit()
        if template_cape_name not in existing_cape_names:
            print("Template cape should be a built in cape or added to the list")
            exit()
        new_project_path = os.path.abspath(data.get(fpga_key).get("new-project-path"))
        if not os.path.exists(new_project_path):
            print("The new-project-repo-path specified in {} does not exist".format(new_project_path))
            exit()
        new_project_path = os.path.join(new_project_path, new_cape_name)
        if os.path.exists(new_project_path):
            print("The new-project-repo-path: {} already contains a {} folder".format(new_project_path, new_project_path))
            exit()

        script_args = "SCRIPT_ARGS: ONLY_CREATE_DESIGN PROJECT_LOCATION:" + new_project_path + " PROG_EXPORT_PATH:" + new_project_path
        build_opts = data.get(fpga_key).get("build-opts")
        for opt in build_opts:
            if opt == "top-level-name":
                script_args += " TOP_LEVEL_NAME:{}".format(build_opts[opt])
            if opt == "version":
                script_args += " DESIGN_VERSION:{}".format(build_opts[opt])
            if opt == "cape":
                script_args += " CAPE_OPTION:{}".format(build_opts[opt])
            if opt == "m2":
                if build_opts[opt].upper() == "NONE" or build_opts[opt].upper() == "DEFAULT":
                    script_args += " M2_OPTION:{}".format(build_opts[opt].upper())
                else:
                    print("M2_OPTION must be NONE or DEFAULT, using DEFAULT")
                    script_args += " M2_OPTION:DEFAULT"
            if opt == "syzygy":
                script_args += " SYZYGY_OPTION:{}".format(build_opts[opt])
            if opt == "mipi_csi":
                script_args += " MIPI_CSI_OPTION:{}".format(build_opts[opt])

        print("Script arguments: " + script_args)
        return CustomSource(new_cape_name, template_cape_name, new_project_path, script_args)


# Checks to see if all of the required tools are installed and present in path, if a needed tool isn't available the script will exit
def check_tool_status_linux():
    if shutil.which("libero") is None:
        print("Error: libero not found in path")
        exit()

    if os.environ.get('FPGENPROG') is None:
        print(
            "Error: FPGENPROG environment variable not set, please set this variable and point it to the appropriate "
            "FPGENPROG executable to run this script")
        exit()

    path = os.environ["PATH"]

    if "riscv-unknown-elf-gcc" not in path:
        print(
            "The path to the RISC-V toolchain needs to be set in PATH to run this script")
        exit()


# Creates required folders and removes artifacts before beginning
def init_workspace(source_list, custom_source):
    print("================================================================================")
    print("                              Initialize workspace")
    print("================================================================================\r\n", flush=True)

    # See if the custom cape already exists.
    with open(source_list) as f:  # open the yaml file passed as an arg
        data = yaml.load(f, Loader=yaml.FullLoader)

        template_cape = custom_source.template_name
        new_cape = custom_source.new_cape_name
        # See if the custom cape exists
        new_cape_path = os.path.join(cape_dir_path, new_cape)
        print("Checking for existing cape in: ", new_cape_path)
        if os.path.exists(new_cape_path):
            print("Existing cape found", new_cape_path)
            if force_delete:
                print("Force flag set. Deleting: ", new_cape_path)
                shutil.rmtree(new_cape_path)
            else:
                print("Using existing cape: ", new_cape_path)
                return
            
        print("Cloning {}, into {}".format(template_cape, new_cape))
        new_cape_path = os.path.join(cape_dir_path, new_cape)
        shutil.copytree(os.path.join(cape_dir_path, template_cape), new_cape_path)
        for root, dirs, files in os.walk(new_cape_path):
            for file_name in files:
                filepath = os.path.join(root, file_name)
                with open(filepath) as f:
                    s = f.read()
                pattern = r"\b" + re.escape(template_cape) + r"\b"
                s = re.sub(pattern, new_cape , s)
                with open(filepath, "w") as f:
                    f.write(s)


def generate_libero_project(libero, yaml_input_file, custom_source):
    print("================================================================================")
    print("                            Generate Libero project")
    print("================================================================================\r\n", flush=True)
    # Execute the Libero TCL script used to create the Libero design
    initial_directory = os.getcwd()
    os.chdir("./sources/FPGA-design")
    script = os.path.join( gateware_repo_path, "sources", "FPGA-design", "BUILD_BVF_GATEWARE.tcl")

    libero_cmd = libero + " SCRIPT:" + script + " \"" + custom_source.script_args + "\""
    print("Libero command: " + libero_cmd, flush=True)
    os.system(libero_cmd)
    os.chdir(initial_directory)


def main():
    global libero

    parse_arguments()

    config = validate_input(yaml_input_file)

    # This function will check if all of the required tools are present and quit if they aren't
    check_tool_status_linux()

    init_workspace(yaml_input_file, config)

    generate_libero_project(libero, yaml_input_file, config)

    print("Finished", flush=True)


if __name__ == '__main__':
    main()

