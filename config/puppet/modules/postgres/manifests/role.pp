# Based on work by Luke Kanies, luke@madstop.com
# https://github.com/lak/puppet-postgres

define postgres::role($ensure, $password = false, $superuser = false, $login = true) {
    $passtext = $password ? {
        false => "",
        default => "PASSWORD '$password'"
    }
    $supertext = $superuser ? {
        false => "",
        default => "SUPERUSER"
    }
    $logintext = $login ? {
        false => "NOLOGIN",
        default => "LOGIN"
    }

    case $ensure {
        present: {
            exec { "Create $name postgres role":
                command => "/usr/bin/psql -c \"CREATE ROLE $name WITH $passtext $supertext $logintext\"",
                user => "postgres",
                unless => "/usr/bin/psql -c '\\du' | grep '^  *$name  *|'"
            }
        }
        absent:  {
            exec { "Remove $name postgres role":
                command => "/usr/bin/dropuser $name",
                user => "postgres",
                onlyif => "/usr/bin/psql -c '\\du' | grep '$name  *|'"
            }
        }
        default: {
            fail "Invalid 'ensure' value '$ensure' for postgres::role"
        }
    }
}
