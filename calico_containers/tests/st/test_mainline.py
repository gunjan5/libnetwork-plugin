import unittest
import uuid
from subprocess import CalledProcessError
from functools import partial

from test_base import TestBase
from docker_host import DockerHost
from utils import retry_until_success


class TestMainline(TestBase):
    def run_mainline(self, ip1, ip2):
        """
        Setup two endpoints on one host and check connectivity.
        """
        host = DockerHost('host')
        net_name = str(uuid.uuid4())

        host.execute("docker network create --driver=calico %s" %
                     net_name)
        host.execute("docker run --net=%s -tid --name=node1 busybox" %
                     net_name)
        host.execute("docker run --net=%s -tid --name=node2 busybox" %
                     net_name)

        # Perform a docker inspect to extract the configured IP addresses.
        node1_ip = host.execute("docker inspect --format "
                                "'{{ .NetworkSettings.IPAddress }}' "
                                "node1").rstrip()
        node2_ip = host.execute("docker inspect --format "
                                "'{{ .NetworkSettings.IPAddress }}' "
                                "node2").rstrip()
        if ip1 != 'auto':
            self.assertEqual(ip1, node1_ip)
        if ip2 != 'auto':
            self.assertEqual(ip2, node2_ip)

        ping = partial(host.execute,
                       "docker exec node1 ping %s -c 1 -W 1" % node2_ip)
        retry_until_success(ping, ex_class=CalledProcessError)

        # Check connectivity.
        host.execute("docker exec node1 ping %s -c 1 -W 1" % node1_ip)
        host.execute("docker exec node1 ping %s -c 1 -W 1" % node2_ip)
        host.execute("docker exec node2 ping %s -c 1 -W 1" % node1_ip)
        host.execute("docker exec node2 ping %s -c 1 -W 1" % node2_ip)

        # Test calicoctl teardown commands.
        host.execute("docker rm -f node1")
        host.execute("docker rm -f node2")
        host.calicoctl("pool remove 192.168.0.0/16")
        host.calicoctl("node stop")

    def test_auto(self):
        """
        Run the test using auto assignment of IPs
        """
        self.run_mainline("auto", "auto")

    @unittest.skip("Docker Driver doesn't support static IP assignment yet.")
    def test_hardcoded_ip(self):
        """
        Run the test using hard coded IPV4 assignments.
        """
        self.run_mainline("192.168.1.1", "192.168.1.2")
