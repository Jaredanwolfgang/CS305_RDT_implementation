# Please create conda kernel: conda create -n <name> python=3.9.0 first
import RDT
client = RDT.RDTSocket()
client.bind(('127.0.0.1', 2346))
client.listen(5)
client.connect(('127.0.0.1', 2345))
