from enum import Enum


class SessionRequestTypes(str, Enum):
    ASSOCIATE = "ASSOCIATE"
    KEY_EXCHANGE = "KEY_EXCHANGE"
    FORWARD = "FORWARD"

