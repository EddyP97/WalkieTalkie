from WalkieTalkieLogic import WalkieLogic
import CommandSender
import stmpy
import logging
from threading import Thread
import json



def main():
    """
    Start the component.
    """

    # we start the stmpy driver and add 2 walkies
    stm_driver = stmpy.Driver()
    print(1)
    stm_driver.add_machine(WalkieLogic.create_machine(name = "1"))
    stm_driver.add_machine(WalkieLogic.create_machine(name = "2"))
    print(2)

    stm_driver.start(keep_active=True)

    command = CommandSender.CommandSenderComponent()

def stop():
    # stop the state machine Driver
    stm_driver.stop()


#if __name__ == "__main__":
#    main()

# logging.DEBUG: Most fine-grained logging, printing everything
# logging.INFO:  Only the most important informational log items
# logging.WARN:  Show only warnings and errors.
# logging.ERROR: Show only error messages.

debug_level = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


m = main()