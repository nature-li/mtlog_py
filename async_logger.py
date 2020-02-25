# -*- coding:utf8 -*-

import os
import logging
import datetime
import traceback
import inspect
import multiprocessing
import threading
import queue
import psutil
from .mt_file_hanlder import MtTimedFileHandler


# log environment
class LogEnv(object):
    product = "product"
    abtest = "abtest"
    develop = "develop"


# log severity
class LogSev(object):
    quit = (80, "quit")
    report = (70, "report")
    fatal = (60, "fatal")
    error = (50, "error")
    warn = (40, "warn")
    info = (30, "info")
    debug = (20, "debug")
    trace = (10, "trace")


class InnerLogger(object):
    def __init__(self):
        self.__process = None
        self.__report = None

    def init(self, target, file_name, file_size=100 * 1024 * 1024, max_file_count=-1):
        """ Initialize logger

        :type target: string
        :type file_name: string
        :type file_size: int
        :type max_file_count: int
        :return: bool
        """
        try:
            # Create log path if not existing
            if not os.path.exists(target):
                os.mkdir(target)

            # Define log level
            logging.addLevelName(LogSev.trace[0], LogSev.trace[1])
            logging.addLevelName(LogSev.debug[0], LogSev.debug[1])
            logging.addLevelName(LogSev.info[0], LogSev.info[1])
            logging.addLevelName(LogSev.warn[0], LogSev.warn[1])
            logging.addLevelName(LogSev.error[0], LogSev.error[1])
            logging.addLevelName(LogSev.fatal[0], LogSev.fatal[1])
            logging.addLevelName(LogSev.report[0], LogSev.report[1])

            # Set log format
            formatter = logging.Formatter('%(message)s')

            # Process logger to process.log
            process_file = os.path.join(target, file_name + '.process.log')
            process_handler = MtTimedFileHandler(process_file, file_size, max_file_count)
            process_handler.setLevel(LogSev.trace[0])
            process_handler.setFormatter(formatter)
            process_logger = logging.getLogger("process")
            process_logger.setLevel(LogSev.trace[0])
            process_logger.addHandler(process_handler)
            self.__process = process_logger

            # Report logger to report.log
            report_file = os.path.join(target, file_name + '.report.log')
            report_handler = MtTimedFileHandler(report_file, file_size, max_file_count)
            report_handler.setLevel(LogSev.trace[0])
            report_handler.setFormatter(formatter)
            report_logger = logging.getLogger("report")
            report_logger.setLevel(LogSev.trace[0])
            report_logger.addHandler(report_handler)
            self.__report = report_logger
            return True
        except:
            print(traceback.format_exc())
            return False

    def trace(self, message):
        try:
            self.__process.log(LogSev.trace[0], message)
        except:
            print(traceback.format_exc())

    def debug(self, message):
        try:
            self.__process.log(LogSev.debug[0], message)
        except:
            print(traceback.format_exc())

    def info(self, message):
        try:
            self.__process.log(LogSev.info[0], message)
        except:
            print(traceback.format_exc())

    def warn(self, message):
        try:
            self.__process.log(LogSev.warn[0], message)
        except:
            print(traceback.format_exc())

    def error(self, message):
        try:
            self.__process.log(LogSev.error[0], message)
        except:
            print(traceback.format_exc())

    def fatal(self, message):
        try:
            self.__process.log(LogSev.fatal[0], message)
        except:
            print(traceback.format_exc())

    def report(self, message):
        try:
            self.__report.log(LogSev.report[0], message)
        except:
            print(traceback.format_exc())


class AsyncLogger(object):
    __inner_logger = None
    __sep = '\x1E'
    __env = LogEnv.develop
    __queue = multiprocessing.Queue()
    __process = None
    __level_number = LogSev.info[0]

    @classmethod
    def start(cls, env, target, file_name, file_size=100 * 1024 * 1024, max_file_count=-1, locker=None):
        cls.__env = env
        cls.__process = multiprocessing.Process(target=cls.consume,
                                                name="AsyncLogger",
                                                args=(cls.__queue, target, file_name, file_size, max_file_count))
        cls.__process.start()

    @classmethod
    def stop(cls, block=True):
        cls.__queue.put((LogSev.quit, "quit"))
        if block:
            cls.__process.join()

    @classmethod
    def set_level(cls, level):
        cls.__level_number = level[0]

    @classmethod
    def __message(cls, msg, level=LogSev.info, pvid="", keyword="normal"):
        try:
            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file_name = info.filename
            line_number = info.lineno
            function = info.function
            message = cls.json_message(level, file_name, line_number, function, pvid, keyword, msg)
            return message
        except:
            return None

    @classmethod
    def consume(cls, q, target, file_name, file_size, max_file_count):
        cls.__inner_logger = InnerLogger()
        cls.__inner_logger.init(target, file_name, file_size, max_file_count)
        message = cls.__message("async logger is starting...")
        cls.__inner_logger.info(message)

        parent = psutil.Process(os.getpid()).parent()
        while True:
            try:
                (level, message) = q.get(block=True, timeout=5)
                if level[0] == LogSev.trace[0]:
                    cls.__inner_logger.trace(message)
                    # pass
                elif level[0] == LogSev.debug[0]:
                    cls.__inner_logger.debug(message)
                    # pass
                elif level[0] == LogSev.info[0]:
                    cls.__inner_logger.info(message)
                    # pass
                elif level[0] == LogSev.warn[0]:
                    cls.__inner_logger.warn(message)
                    # pass
                elif level[0] == LogSev.error[0]:
                    cls.__inner_logger.error(message)
                    # pass
                elif level[0] == LogSev.fatal[0]:
                    cls.__inner_logger.fatal(message)
                    # pass
                elif level[0] == LogSev.report[0]:
                    cls.__inner_logger.report(message)
                    # pass
                elif level[0] == LogSev.quit[0]:
                    break
                else:
                    print("invalid level")
            except queue.Empty:
                if not parent.is_running():
                    break
                continue

        message = cls.__message("async logger is stopping...")
        cls.__inner_logger.info(message)

    @classmethod
    def trace(cls, msg, pvid="", keyword="normal"):
        try:
            if LogSev.trace[0] < cls.__level_number:
                return True
            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file_name = info.filename
            line_number = info.lineno
            function = info.function
            message = cls.json_message(LogSev.trace, file_name, line_number, function, pvid, keyword, msg)
            cls.__queue.put((LogSev.trace, message))
            return True
        except:
            print(traceback.format_exc())

    @classmethod
    def debug(cls, msg, pvid="", keyword="normal"):
        try:
            if LogSev.debug[0] < cls.__level_number:
                return True
            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file_name = info.filename
            line_number = info.lineno
            function = info.function
            message = cls.json_message(LogSev.debug, file_name, line_number, function, pvid, keyword, msg)
            cls.__queue.put((LogSev.debug, message))
            return True
        except:
            print(traceback.format_exc())

    @classmethod
    def info(cls, msg, pvid="", keyword="normal"):
        try:
            if LogSev.info[0] < cls.__level_number:
                return True
            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file_name = info.filename
            line_number = info.lineno
            function = info.function
            message = cls.json_message(LogSev.info, file_name, line_number, function, pvid, keyword, msg)
            cls.__queue.put((LogSev.info, message))
            return True
        except:
            print(traceback.format_exc())

    @classmethod
    def warn(cls, msg, pvid="", keyword="normal"):
        try:
            if LogSev.warn[0] < cls.__level_number:
                return True
            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file_name = info.filename
            line_number = info.lineno
            function = info.function
            message = cls.json_message(LogSev.warn, file_name, line_number, function, pvid, keyword, msg)
            cls.__queue.put((LogSev.warn, message))
            return True
        except:
            print(traceback.format_exc())

    @classmethod
    def error(cls, msg, pvid="", keyword="normal"):
        try:
            if LogSev.error[0] < cls.__level_number:
                return True
            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file_name = info.filename
            line_number = info.lineno
            function = info.function
            message = cls.json_message(LogSev.error, file_name, line_number, function, pvid, keyword, msg)
            cls.__queue.put((LogSev.error, message))
            return True
        except:
            print(traceback.format_exc())

    @classmethod
    def fatal(cls, msg, pvid="", keyword="normal"):
        try:
            if LogSev.fatal[0] < cls.__level_number:
                return True
            frame = inspect.currentframe().f_back
            info = inspect.getframeinfo(frame)
            file_name = info.filename
            line_number = info.lineno
            function = info.function
            message = cls.json_message(LogSev.fatal, file_name, line_number, function, pvid, keyword, msg)
            cls.__queue.put((LogSev.fatal, message))
            return True
        except:
            print(traceback.format_exc())

    @classmethod
    def json_message(cls, level, file_name, line_number, function, pvid, keyword, msg):
        try:
            if not isinstance(file_name, (str,)):
                file_name = str(file_name)
            if not isinstance(line_number, (str,)):
                line_number = str(line_number)
            if not isinstance(function, (str,)):
                function = str(function)
            if not isinstance(pvid, (str,)):
                pvid = str(pvid)
            if not isinstance(keyword, (str,)):
                keyword = str(keyword)
            if not isinstance(msg, (str,)):
                msg = str(msg)
            now = datetime.datetime.now()
            message = ""
            message += "[" + now.strftime("%Y-%m-%d %H:%M:%S.%f") + "]" + cls.__sep
            message += "[" + level[1] + "]" + cls.__sep
            message += "[" + str(os.getpid()) + "@" + str(threading.current_thread().ident) + "]" + cls.__sep
            message += "[" + file_name + ":" + line_number + ":" + function + "]" + cls.__sep
            message += "[" + cls.__env + "]" + cls.__sep
            message += "[" + pvid + "]" + cls.__sep
            message += "[" + keyword + "]" + cls.__sep
            message += "[" + msg + "]" + cls.__sep
            return message
        except:
            print(traceback.format_exc())
