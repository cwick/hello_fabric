class provision {
    ############################################################################
    # Set up users and SSH access
    ############################################################################
    user { "cwick":
         ensure     => present,
         comment    => "Carmen Wick",
         managehome => true,
         shell      => "/bin/bash",
    }

    ssh_authorized_key { "carmen@icecube":
        ensure => present,
        key => "AAAAB3NzaC1yc2EAAAADAQABAAABAQDgcXorY4YazGbaMG3nv0bVJ7ykpANIrGc4WRR8H7uol2fb5PD0SyPoEeE/PIUX0vnaleG1vqz9C4O7Ykz2ktC/O1R4T0Cu5lEhPKzkSMxFiG5DtQuIMezDIbpD/AoEBqQYHhdJiL+fGTsyZ+PE6lnSsKK71O4A2Tj3l8qxediWFjMpGqpKzWlSNAKr/7uBo0v4JsmGz8Oa80MLozFpDOTY2fiN9eW2pm6zEDufzejHU78g/EqYyrLbyLhvy2Z+QlqA1QFi3XHHC0+a71zYm7aSGhsCFCzk0j2NQVFsPZOyBfTTQLcQupzkZDxijYyoOtQ5Ufg04BIzmJ8xHpvPyIcl",
        type => "ssh-rsa",
        user => "cwick",
    }

    file { "/etc/ssh/sshd_config":
        ensure => file,
        mode   => 644,
        owner  => "root",
        group  => "root",
        source => "puppet:///modules/provision/sshd_config",
    }

    service { "ssh":
        ensure     => running,
        enable     => true,
        hasrestart => true,
        hasstatus  => true,
        # Automatically restart when config file changes
        subscribe  => File["/etc/ssh/sshd_config"],
    }

    ############################################################################
    # Set system hostname
    ############################################################################
    file { "/etc/hosts":
        ensure   => file,
        mode     => 644,
        owner    => "root",
        group    => "root",
        content  => template("provision/hosts.erb"),
        before   => File["/etc/hostname"],
    }
    
    file { "/etc/hostname":
        ensure => file,
        mode   => 644,
        owner  => "root",
        group  => "root",
        content => "newton\n"
    }

    exec { "/bin/hostname -F /etc/hostname":
        subscribe   => File["/etc/hostname"],
        refreshonly => true
    }

    file { "/etc/default/dhcpcd":
        ensure => file,
        mode   => 644,
        owner  => "root",
        group  => "root",
        source => "puppet:///modules/provision/dhcpcd",
    }

    ############################################################################
    # Set up timezone and locale
    ############################################################################
    file { "/etc/localtime":
        ensure => "/usr/share/zoneinfo/America/Los_Angeles",
    } 
    file { "/etc/timezone":
        content => "America/Los_Angeles\n", 
    } 
    file { "/etc/default/locale":
        content => "LANG=\"en_US.UTF-8\"",
    }
    
    ############################################################################
    # Misc stuff
    ############################################################################    
    file { "/etc/sudoers":
        owner  => root,
        group  => root,
        mode   => 440,
        source => "puppet:///modules/provision/sudoers",
    }
}
