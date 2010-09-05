import socket, time, string, sys, urlparse, uuid, signal, select

from threading import *

class PackageReceiver(Thread):

	def __init__(self, uuid, port=None):
		Thread.__init__(self)
		port = port or 0
		self.uuid = uuid
		self.stopping = False
		
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.bind(('', port))
		self.port = self.server.getsockname()[1]
		self.server.listen(1)
		print 'Listening on port %d' % self.port
		
		self.client = None
		
		#signal.signal(signal.SIGINT, self.sighandler)
	
	def run(self):
		while not self.stopping:
			rr, rw, rx = select.select([self.server], [], [], 1)
			if self.server in rr:
				self.client, address = self.server.accept()
				self.transfer()
				break
		self.server.shutdown(socket.SHUT_RDWR)
		self.server.close()
	
	def transfer(self):
		print 'Starting media transfer for %s' % self.uuid
		
		f = open('%s.tar.gz' % self.uuid, 'wb')
		while 1:
			data = self.client.recv(1024)
			if not data:
				break
			f.write(data)
		f.close()

		print 'Closing media transfer'
	
	def close(self):
		print 'Shutting down sockets...'
		self.server.shutdown(socket.SHUT_RDWR)
		self.server.close()
		
		if self.client is not None:
			self.client.shutdown(socket.SHUT_RDWR)
			self.client.close()
		
	
	def sighandler(self, signum, frame):
		self.stopping = True