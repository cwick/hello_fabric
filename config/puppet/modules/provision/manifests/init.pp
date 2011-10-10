class provision ($hostname) {
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
        content => "${hostname}\n"
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
    # Install packages
    ############################################################################
    exec { "apt-get update":
        path => "/usr/bin",
    }
    package { "nginx":
        ensure => present
    }
    package { "python":
        ensure => present
    }
    package { "python-pip":
        ensure => present
    }
    package { "python-dev":
        ensure => present
    }
    package { "postgresql":
        ensure => present
    }
    package { "libpq-dev":
        ensure => present
    }
    package { "memcached":
        ensure => present
    }
    package { "openjdk-6-jre-headless":
        ensure => present
    }
    Package { require => Exec["apt-get update"] }

    ############################################################################
    # Install Solr
    ############################################################################
    $solr_url = "http://www.takeyellow.com/apachemirror/lucene/solr/3.4.0/"
    $solr_version = "apache-solr-3.4.0"
    $solr_archive = "apache-solr-3.4.0.zip"

    user { "solr": ensure => present }
    file { "/usr/local/src": ensure => directory }
    exec { "wget ${solr_url}${solr_archive} -O /usr/local/src/${solr_archive}":
        creates => "/usr/local/src/${solr_archive}",
        alias   => "download-solr",
        require => File["/usr/local/src"],
        path    => "/usr/bin",
    }
    exec { "unzip ${solr_archive}":
        alias   => "unzip-solr",
        cwd     => "/usr/local/src",
        creates => "/usr/local/src/${solr_version}",
        require => [Exec["download-solr"], Package["unzip"]],
        path    => "/usr/bin",
    }
    file { "/opt/solr":
        ensure  => directory,
        owner   => "solr",
        group   => "solr",
        mode    => 644,
        recurse => true,
        require => Exec["install-solr"],
    }
    exec { "cp -R ${solr_version}/example/ /opt/solr/":
        creates => "/opt/solr/",
        alias   => "install-solr",
        path    => "/bin",
        require => Exec["unzip-solr"],
        cwd     => "/usr/local/src",
    }
    package { "unzip":
        ensure => present,
    }
    
    ############################################################################
    # Configure memcached
    ############################################################################
    # Each application will manage its own memcached instance
    service { "memcached":
        require    => Package["memcached"],
        ensure     => stopped,
        enable     => false,
        hasrestart => true,
        hasstatus  => true,
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
