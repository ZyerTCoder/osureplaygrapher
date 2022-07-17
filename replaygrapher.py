import sys
import os
import argparse
import logging
from time import time
import leb128
import io

APP_NAME = "OsuReplayGrapher"
VERSION = 1
WORKING_DIR = r"C:\Users\AZM\Documents\Python\osureplaygrapher"
LOG_FILE = f'{APP_NAME}v{VERSION}log.txt'

OSU_LOCATION = r"C:\Users\AZM\AppData\Local\osu!"

'''
Timeline:
V1: 2021 30 09
able to separate the replay binary into its components for standard only
calcs acc and pastes to a csv
'''


def decode_string(hex, p):
    # getting beatmap md5 hash
    if hex[p:p+2] == "0b":
        p += 2
        _t = hex[p:]
        uleb_input = io.BytesIO(bytearray.fromhex(_t))
        md5_hash_length, uleb_length = leb128.u.decode_reader(uleb_input)
        p += uleb_length * 2    # in bytes so 2 hex's for each
        # now find the string
        md5_hash = hex[p:p+md5_hash_length*2] # again, length is in bytes and convert to 
        p += md5_hash_length*2
        decoded_hash = bytes.fromhex(md5_hash).decode()
        return decoded_hash, p
    else:
        p += 2
        return -1, p

def decode_byte(hex, p):
    return int(hex_reverse(hex[p:p+2]), base=16), p + 2

def decode_short(hex, p):
    return int(hex_reverse(hex[p:p+4]), base=16), p + 4

def decode_int(hex, p):
    return int(hex_reverse(hex[p:p+8]), base=16), p + 8

def decode_long(hex, p):
    return int(hex_reverse(hex[p:p+16]), base=16), p + 16

def hex_reverse(hex):
    # to deal with little endians
    return "".join([hex[i:i+2] for i in range(0,len(hex),2)][::-1])

def isolate_replay(hex, length, p):
    replay_data = hex[p:p+(length << 1)]
    return replay_data, p+(length << 1)

def decode_replay(hex):
    content = {}
    p = 0 # pointer for hex

    content["game mode"], p = decode_byte(hex, p)
    if content["game mode"] != 0:
        logging.info("Replay not standard, skipping.")
    
    content["game version"], p = decode_int(hex, p)

    content["beatmap hash"], p = decode_string(hex, p)
    content["player name"], p = decode_string(hex, p)
    content["replay hash"], p = decode_string(hex, p)

    content["300s"], p = decode_short(hex, p)
    content["100s"], p = decode_short(hex, p)
    content["50s"], p = decode_short(hex, p)
    content["gekis"], p = decode_short(hex, p)
    content["katus"], p = decode_short(hex, p)
    content["misses"], p = decode_short(hex, p)

    content["score"], p = decode_int(hex, p)
    content["combo"], p = decode_short(hex, p)
    content["fc?"], p = decode_byte(hex, p)
    content["mods"], p = decode_int(hex, p)

    content["life bar"], p = decode_string(hex, p)

    content["timestamp"], p = decode_long(hex, p)
    
    content["replay length"], p = decode_int(hex, p) # in bytes
    content["replay data"], p = isolate_replay(hex, content["replay length"], p)

    content["online score id"], p = decode_long(hex, p)

    if len(hex[p:])/2 > 0:
        logging.warning(f"Bytes leftover on the replay: {len(hex[p:])/2}")
    return content

def calc_acc(replay):
    total_objects = replay["300s"] + replay["100s"] + replay["50s"] + replay["misses"]
    total_weight = total_objects*300
    if total_weight == 0:
        logging.warning("Replay has no objects, setting acc to -1 and skipping")
        return -1

    _300s_weight = replay["300s"]*300
    _100s_weight = replay["100s"]*100
    _50s_weight = replay["50s"]*50

    return (_300s_weight+_100s_weight+_50s_weight)/total_weight
    

def main(args):
    replays = os.listdir(OSU_LOCATION + r"\Data\r")
    with open(args.out, "w") as out:
        out.write("game version,beatmap hash,player name,300s,100s,50s,misses,score,combo,timestamp,acc\n")
    counter = 0
    for replay in replays:
        if not replay.endswith("osr"):
            continue
        counter += 1
        replay_path = OSU_LOCATION + r"\Data\r\\" + replay
        logging.info(f"Checking replay: {replay_path}")
        with open(replay_path, "rb") as data:
            stuff = data.read()
            hex = bytes.hex(stuff)
        replay_content = decode_replay(hex)
        acc = calc_acc(replay_content)
        values = [
            replay_content["game version"],
            replay_content["beatmap hash"],
            replay_content["player name"],
            replay_content["300s"],
            replay_content["100s"],
            replay_content["50s"],
            replay_content["misses"],
            replay_content["score"],
            replay_content["combo"],
            replay_content["timestamp"],
            acc
            ]
        values = [str(i) for i in values]
        with open(args.out, "a") as out:
            out.write(",".join(values)+"\n")
    logging.info(f"Went through {counter} replays")
        

if __name__ == '__main__':
    t0 = time()
    os.chdir(WORKING_DIR)

    # parse input
    parser = argparse.ArgumentParser(description="OsuReplayGrapher")
    parser.add_argument("-log", type=str, default="INFO", help="set log level for console output, WARNING/INFO/DEBUG")
    parser.add_argument("-logfile", type=str, default="DEBUG", help="sets file logging level, 0/CRITICAL/ERROR/WARNING/INFO/DEBUG, set to 0 to disable")
    parser.add_argument("-out", type=str, default="out.csv", help="name of output file")
    
    args = parser.parse_args()

    # setting up logger to info on terminal and debug on file
    log_format=logging.Formatter(f'%(asctime)s {APP_NAME} v{VERSION} %(levelname)s:%(name)s:%(funcName)s %(message)s')
    
    if args.logfile != "0":
        file_handler = logging.FileHandler(filename=LOG_FILE, mode="a")
        file_handler.setLevel(getattr(logging, args.logfile.upper()))
        file_handler.setFormatter(log_format)
        logging.getLogger().addHandler(file_handler)
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(getattr(logging, args.log.upper()))
    logging.getLogger().addHandler(stream_handler)

    if args.logfile != "0":
        logging.getLogger().setLevel(getattr(logging, args.logfile.upper()))
    else:
        logging.getLogger().setLevel(getattr(logging, args.log.upper()))

    logging.debug(f"Started with arguments: {sys.argv}")

    main(args)

    logging.info(f"Exited. Took {round(time() - t0, 3)}s")