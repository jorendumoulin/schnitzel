/******************************************************************************
* Copyright (C) 2023 Advanced Micro Devices, Inc. All Rights Reserved.
* SPDX-License-Identifier: MIT
******************************************************************************/
/*
 * helloworld.c: simple test application
 *
 * This application configures UART 16550 to baud rate 9600.
 * PS7 UART (Zynq) is not initialized by this application, since
 * bootrom/bsp configures it to baud rate 115200
 *
 * ------------------------------------------------
 * | UART TYPE   BAUD RATE                        |
 * ------------------------------------------------
 *   uartns550   9600
 *   uartlite    Configurable only in HW design
 *   ps7_uart    115200 (configured by bootrom/bsp)
 */

#include <stdio.h>
#include "platform.h"
#include "xil_printf.h"
#include "xil_io.h"
#include "xparameters.h"

/* FPGATop is mapped by the Vivado address editor and exported in the BSP. */
#define FPGA_CTRL_BASEADDR XPAR_FPGATOP_0_BASEADDR

#define FPGA_REG_RUN       0x00U
#define FPGA_REG_STATUS    0x04U
#define FPGA_REG_RELEASE   0x08U
#define FPGA_REG_BARRIERS  0x0cU
#define FPGA_REG_AXI_ERROR 0x10U

static void exercise_axi(void)
{
    u32 status;
    u32 barriers;
    u32 error;

    xil_printf("AXI test at 0x%08x\r\n", FPGA_CTRL_BASEADDR);

    /* Stop the cluster and clear any stale downstream AXI error. */
    Xil_Out32(FPGA_CTRL_BASEADDR + FPGA_REG_RUN, 0U);
    Xil_Out32(FPGA_CTRL_BASEADDR + FPGA_REG_AXI_ERROR, 1U);

    status = Xil_In32(FPGA_CTRL_BASEADDR + FPGA_REG_STATUS);
    barriers = Xil_In32(FPGA_CTRL_BASEADDR + FPGA_REG_BARRIERS);
    error = Xil_In32(FPGA_CTRL_BASEADDR + FPGA_REG_AXI_ERROR);
    xil_printf("AXI read status=0x%08x barriers=%u error=%u\r\n",
               status, barriers, error);

    /* Start the cluster, then queue a release token for the barrier. */
    Xil_Out32(FPGA_CTRL_BASEADDR + FPGA_REG_RUN, 1U);
    status = Xil_In32(FPGA_CTRL_BASEADDR + FPGA_REG_STATUS);
    xil_printf("AXI write RUN=1, status=0x%08x\r\n", status);

    Xil_Out32(FPGA_CTRL_BASEADDR + FPGA_REG_RELEASE, 1U);
    status = Xil_In32(FPGA_CTRL_BASEADDR + FPGA_REG_STATUS);
    xil_printf("AXI write RELEASE=1, status=0x%08x\r\n", status);
}


int main()
{
    init_platform();

    print("Hello World\n\r");
    exercise_axi();
    print("Successfully ran Hello World application\n\r");
    cleanup_platform();
    return 0;
}
