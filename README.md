# beaglev-fpga-workflow

Some automation scripts that I created to streamline the process of creating new FPGA based capes for my BeagleV-Fire development board. It preserves as much functionality from the original ```build-bitstream.py``` script as possible. It checks for the presence of tools, correct file locations, and performs other user input validation to help guide the user to successful project creation.

Usage:

1. Update the ```custom.yaml``` file with the information specific to your project.
    - The ```custom-gateware``` key defines the Libero project that will be created, the other two keys are ignored.
    - Type must be set to ```custom-source``` for the ```build-libero-project.py``` script to detect it.
    - The ```cape-name``` is the name of your custom cape. The ```&cape-name``` is a YAML reference and should be left alone. Only replace ```CUSTOM_FPGA``` with your new name.
    - ```cape-template``` is the shipping CAPE that you want to use as a template. These are assumed to be locaed in [/gateware/sources/FPGA-design/script_support/components/CAPE](https://openbeagle.org/beaglev-fire/gateware/-/tree/main/sources/FPGA-design/script_support/components/CAPE?ref_type=heads) and this is where the new ```CUSTOM_FPGA``` cape will be created.
    - ```new-project-path``` defines the location of the generated Libero project.
    - ```build-opts``` defines the build options for the custom FPGA and project creation. They are parsed and used to create the ```SCRIPT_ARGS``` documented in [/gateware/sources/FPGA-design](https://openbeagle.org/beaglev-fire/gateware/-/tree/main/sources/FPGA-design?ref_type=heads)
      - top-level-name: fpga-widget
      - version: 0.0.1
      - cape: *cape-name
      - m2: NONE
      - syzygy: NONE
      - mipi_csi: NONE
1. Run the ```build-libero-project.py``` script from the root directory of the [gateware](https://openbeagle.org/beaglev-fire/gateware) repository. It accepts an optional ```--force``` flag and the path of the confutation file. If the ```--force``` option is used and an existing custom FPGA cape with the same name is found, the existing cape will be deleted and a new one created. Without the ```--force``` flag, the script will terminate if an existing cape is found.

    ```console
    user:~/repos/gateware $ python3 ./build-libero-project.py -f ./build-options/custom.yaml
    ```

Note: This scrip currently only automates the custom cape creation and project generation. After the project is modified with the new FPGA content, the output files have to be manually copied/exported back into the original [CAPE](https://openbeagle.org/beaglev-fire/gateware/-/tree/main/sources/FPGA-design/script_support/components/CAPE?ref_type=heads) folder and the normal process of executing the ```build-bitsream.py``` script should be followed. The ```build-bitsream.py``` should ignore the ```type: custom-source``` item in the YAML file and will use the ```type: sources``` key for building the bitstream. If there are issues with the ```type: custom-source``` key during bitstream creation, simply remove it.

