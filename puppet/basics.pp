service { ["iptables", "ntpd", "sshd"] : 
	enable => true,
}

package { ["vim-enhanced", "elinks"]:
	ensure => "installed"
}
