/*! \file fetch_dac.c
  *
  * Supporting Fetch DSL
  *
  * \sa fetch.c
  * @defgroup fetch_dac Fetch DAC
  * @{
  */

/*!
 * <hr>
 *
 *  In ChibiOS 2.6.x there is no DAC module in the HAL. It is available
 *  in the kernel_3_dev branch.
 *
 * <hr>
 */

#include <stdint.h>
#include <math.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <ctype.h>

#include "hal.h"
#include "chprintf.h"

#include "util_general.h"
#include "util_strings.h"
#include "util_messages.h"
#include "util_io.h"

#include "fetch_defs.h"
#include "fetch.h"

//#include "dac.h"
#include "fetch_dac.h"

/* Reference STF4 Reference
 *   Once the DAC channelx is enabled, the corresponding GPIO pin (PA4 or PA5) is
 *   automatically connected to the analog converter output (DAC_OUTx). In order to avoid
 *   parasitic consumption, the PA4 or PA5 pin should first be configured to analog (AIN).
 */
SPIConfig spi4_cfg;
DACConfig dac1_cfg;

static bool fetch_dac_help_cmd(BaseSequentialStream * chp, char * cmd_list[], char * data_list[]);
static bool fetch_dac_config_cmd(BaseSequentialStream * chp, char * cmd_list[], char * data_list[]);
static bool fetch_dac_write_cmd(BaseSequentialStream * chp, char * cmd_list[], char * data_list[]);
static bool fetch_dac_reset_cmd(BaseSequentialStream * chp, char * cmd_list[], char * data_list[]);

static fetch_command_t fetch_dac_commands[] = {
    { fetch_dac_help_cmd,   "help",   "DAC command help" },
    { fetch_dac_write_cmd,  "write",  "Write values to DAC\nUsage: write(<channel>, <value>)" },
    { fetch_dac_reset_cmd,  "reset",  "Reset all DAC outputs to 0v" },
    { NULL, NULL, NULL }
  };

static bool external_dac_write(uint16_t channel, uint16_t value)
{
  uint8_t tx_data[2];

  // External DAC -> DAC124S085

  if( channel > 3 || value > 0xfff)
  {
    return false;
  }

  // set channel bits (15..16)
  value |= (channel << 14);

  // set op bits (13..14)
  //
  // 0 = Write to specified register but do not update outputs
  // 1 = Write to specified register and update outputs
  // 2 = Write to all registers and update outputs
  // 3 = Power down outputs
  value |= (1 << 12);

  // make sure the byte order is correct (MSBF 16bit)
  tx_data[0] = value >> 8;
  tx_data[1] = value & 0xff;

  spiSelect(&SPID4);
  spiSend(&SPID4, 2, tx_data);
  spiUnselect(&SPID4);
  
  return true;
}

static bool fetch_dac_help_cmd(BaseSequentialStream * chp, char * cmd_list[], char * data_list[])
{
  if( !fetch_input_check(chp, cmd_list, FETCH_TOK_SUBCMD_0, data_list, 0) )
  {
    return false;
  }

  util_message_info(chp, "Fetch DAC Help:");
  fetch_display_help(chp, fetch_dac_commands);
	return true;
}

static bool fetch_dac_write_cmd(BaseSequentialStream * chp, char * cmd_list[], char * data_list[])
{
  char * endptr;

  if( !fetch_input_check(chp, cmd_list, FETCH_TOK_SUBCMD_0, data_list, 2) )
  {
    return false;
  }

  int32_t channel = strtol(data_list[0],&endptr,0);

  if( *endptr != '\0' ) {
    util_message_error(chp, "invalid channel");
    return false;
  }

  int32_t value = strtol(data_list[1],&endptr,0);

  if( *endptr != '\0' ) {
    util_message_error(chp, "invalid value");
    return false;
  }

  switch(channel)
  {
    case 0:
    case 1:
    case 2:
    case 3:
      return external_dac_write(channel, value);
    case 4:
      dacPutChannelX(&DACD1, 0, value);
      return true;
    default:
      util_message_error(chp, "invalid channel");
      return false;
  }
}

static bool fetch_dac_reset_cmd(BaseSequentialStream * chp, char * cmd_list[], char * data_list[])
{
  if( !fetch_input_check(chp, cmd_list, FETCH_TOK_SUBCMD_0, data_list, 0) )
  {
    return false;
  }

  return fetch_dac_reset(chp);
}


void fetch_dac_init(BaseSequentialStream * chp)
{
  static bool dac_init_flag = false;

  if( dac_init_flag )
    return;

  dac1_cfg.init = 0;
  dac1_cfg.datamode = DAC_DHRM_12BIT_RIGHT;

  dacStart(&DACD1, &dac1_cfg);
  
  spi4_cfg.end_cb = NULL;
  spi4_cfg.ssport = GPIOE;
  spi4_cfg.sspad = GPIOE_SPI4_NSS;
  spi4_cfg.cr1 = SPI_CR1_CPHA;

  spiStart(&SPID4, &spi4_cfg);

  fetch_dac_reset(chp);

  dac_init_flag = true;
}

/*! \brief dispatch an DAC command
 */
bool fetch_dac_dispatch(BaseSequentialStream * chp, char * cmd_list[], char * data_list[])
{
  fetch_dac_init(chp);
  return fetch_dispatch(chp, fetch_dac_commands, cmd_list[FETCH_TOK_SUBCMD_0], cmd_list, data_list);
}

bool fetch_dac_reset(BaseSequentialStream * chp)
{
  dacPutChannelX(&DACD1, 0, 0);
  external_dac_write(0,0);
  external_dac_write(1,0);
  external_dac_write(2,0);
  external_dac_write(3,0);
  return true;
}

//! @}

