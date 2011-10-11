# Based on work by Luke Kanies, luke@madstop.com
# https://github.com/lak/puppet-postgres

define postgres::database($ensure) {
    case $ensure {
        present: {
            exec { "Create $name postgres db":
                command => "/usr/bin/createdb $name",
                user => "postgres",
                unless => "/usr/bin/psql -l | grep '$name  *|'"
            }
        }
        absent:  {
            exec { "Remove $name postgres db":
                command => "/usr/bin/drop $name",
                onlyif => "/usr/bin/psql -l | grep '$name  *|'",
                user => "postgres"
            }
        }
        default: {
            fail "Invalid 'ensure' value '$ensure' for postgres::database"
        }
    }
}

