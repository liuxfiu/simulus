from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from .mailbox import Mailbox
from sortedcontainers import SortedDict
import uuid

if TYPE_CHECKING:
    from simulus import simulator

@dataclass
class _ChannelData_:
    """
    The data structure that a channel will store
    """
    value: Any
    time: int
    # todo: use this for comsume operations
    ref = 0

@dataclass
class _Channel_Read_Request_:
    origin_mb_name: str
    time: int | None = None
    timeout: int | None = None
    # todo: implement different timestamp queries

@dataclass
class _Channel_Write_Request_:
    value: Any
    time: int

@dataclass
class _Channel_Read_Response_:
    data: _ChannelData_ | None
    timedout: bool = False

def channel_name_to_mb_name(channel_name: str):
    return f"STM_Channel_{channel_name}"

class _Channel_:
    """
    A STM channel, which is a data structure that holds timestamped data
    """
    def __init__(self, sim: "simulator", channel_name: str):
        self.sim = sim
        self.channel_dict = SortedDict()
        # requests that are waiting for data
        self.blocked_requests: dict[int, list[_Channel_Read_Request_]] = {}
        self.requests_mb = self.sim.mailbox(channel_name_to_mb_name(channel_name))
        # listen for requests
        self.requests_mb.add_callback(self.handle_request)
    
    def __contains__(self, time: int):
        return time in self.channel_dict
    
    def __getitem__(self, time: int) -> _ChannelData_:
        return self.channel_dict[time]

    def get_oldest(self) -> _ChannelData_:
        _, data = self.channel_dict.peekitem(0)
        return data
    
    def get_oldest_unseen(self) -> _ChannelData_:
        raise NotImplementedError()
    
    def get_newest(self) -> _ChannelData_:
        _, data = self.channel_dict.peekitem(-1)
        return data

    def get_newest_unseen(self) -> _ChannelData_:
        raise NotImplementedError()

    def insert(self, value, time: int):
        data = _ChannelData_(value, time)
        self.channel_dict[time] = data
        # respond to waiting requests
        if time in self.blocked_requests:
            reqs = self.blocked_requests.pop(time)
            for req in reqs:
                self.respond_to_read_request(req, _Channel_Read_Response_(data))
    
    def handle_request(self):
        req: Any | None = self.requests_mb.retrieve(isall=False)
        if not req:
            return
        if isinstance(req, _Channel_Read_Request_):
            self.handle_read_request(req)
        elif isinstance(req, _Channel_Write_Request_):
            self.handle_write_request(req)
        else:
            print("recieved invalid request")
            return
    
    def handle_read_request(self, req: _Channel_Read_Request_):
        if not req.time:
            self.respond_to_read_request(req, _Channel_Read_Response_(self.get_oldest()))
            return
        # block requests
        if req.time not in self:
            if req.time not in self.blocked_requests:
                self.blocked_requests[req.time] = []
            self.blocked_requests[req.time].append(req)
            if req.timeout:
                self.sim.sched(self.create_timeout_handler(req), offset=req.timeout)
            return
        self.respond_to_read_request(req, _Channel_Read_Response_(self[req.time]))

    def respond_to_read_request(self, req: _Channel_Read_Request_, res: _Channel_Read_Response_):
        if req.origin_mb_name in self.sim._mailboxes:
            mb = self.sim._mailboxes[req.origin_mb_name]
            mb.send(res)
        else:
            raise NotImplementedError("STM across simulators not implemented yet")
    
    def create_timeout_handler(self, req: _Channel_Read_Request_):
        def handle_timeout():
            if req.time in self.blocked_requests and req in self.blocked_requests[req.time]:
                self.blocked_requests[req.time].remove(req)
                self.respond_to_read_request(req, _Channel_Read_Response_(None, timedout=True))
        return handle_timeout

    def handle_write_request(self, req: _Channel_Write_Request_):
        self.insert(req.value, req.time)
    
class _Connection_:
    """
    Encapsulates shared connection logic for a STM channel
    """

    def __init__(self, sim: "simulator", chan: str):
        self._sim = sim
        self._chan = chan
        channel_mb_name = channel_name_to_mb_name(chan)
        self.channel_mb = self._sim._mailboxes[channel_mb_name]
        self.mb_name = uuid.uuid4()
        self.mb: Mailbox = self._sim.mailbox(self.mb_name)

class _ConnReader(_Connection_):
    def get(self, time: int | None = None, timeout: int | None = None) -> tuple[Any, bool]:
        "Reads the channel for data at a given time"
        req = _Channel_Read_Request_(self.mb_name, time, timeout)
        self.channel_mb.send(req)
        res = self.mb.recv(isall=False)
        return res.data, res.timedout
    
    def consume(self, time: int):
        "Mark a value in the channel as consumed by this connection"
        raise NotImplementedError("STM garbage collection not implemented yet")


class _ConnWriter(_Connection_):
    def put(self, value, time: int | None = None):
        "Places 'value' as the channel's data at 'time'"
        now = self._sim.now
        if time == None:
            assert isinstance(now, (int, float))
            time = int(now)
        assert time >= now
        self.channel_mb.send(_Channel_Write_Request_(value, time))
