# Please create conda kernel: conda create -n <name> python=3.9.0 first
import RDT
server = RDT.RDTSocket()
server.bind(('127.0.0.1', 2345))
server.accept()