import argparse
import codecs
import sys
import json

from sqlalchemy.engine import create_engine
from sqlalchemy.schema import MetaData
import pkg_resources

from sqlacodegen.codegen import CodeGenerator
from sqlalchemy_utils.types.ltree import LtreeType
from sqlalchemy.dialects.postgresql.base import ischema_names

ischema_names['ltree'] = LtreeType

def main():
    parser = argparse.ArgumentParser(description='Generates SQLAlchemy model code from an existing database.')
    parser.add_argument('url', nargs='?', help='SQLAlchemy url to the database')
    parser.add_argument('--version', action='store_true', help="print the version number and exit")
    parser.add_argument('--schema', help='load tables from an alternate schema')
    parser.add_argument('--tables', help='tables to process (comma-separated, default: all)')
    parser.add_argument('--noviews', action='store_true', help="ignore views")
    parser.add_argument('--noindexes', action='store_true', help='ignore indexes')
    parser.add_argument('--noconstraints', action='store_true', help='ignore constraints')
    parser.add_argument('--nojoined', action='store_true', help="don't autodetect joined table inheritance")
    parser.add_argument('--noinflect', action='store_true', help="don't try to convert tables names to singular form")
    parser.add_argument('--noclasses', action='store_true', help="don't generate classes, only tables")
    parser.add_argument('--outfile', help='file to write output to (default: stdout)')
    parser.add_argument('--audited', help='comma separated list of audited table names')
    parser.add_argument('--auditall', action='store_true', help='audit all tables')
    parser.add_argument('--relationship', action='append', nargs=4, metavar=('parent', 'child', 'name', 'kwargs'), help='Creates an association with the specified name')
    parser.add_argument('--loginuser', help='Model name that will instantiate the flask-login "UserMixin" (default: none)')
    parser.add_argument('--loginrole', help='Model name that will instantiate the flask-login "UserRole" (default: none)')
    args = parser.parse_args()

    if args.version:
        version = pkg_resources.get_distribution('sqlacodegen').parsed_version
        print(version.public)
        return
    if not args.url:
        print('You must supply a url\n', file=sys.stderr)
        parser.print_help()
        return
    _relationship = dict()
    _rel_set = set()
    args.relationship = [] if args.relationship is None else args.relationship
    for (key, child, name, kwargs) in args.relationship:
        val = { 'child' : child,
                'name' : name,
                'kwargs' : json.loads(kwargs)
              }
        if not (key in _relationship):
            _relationship[key] = []
        # There must not be conflicts where a table is given
        # forced relationships that share an an attribute name
        if (key, name) in _rel_set:
            raise KeyError(f'Tried to create a forced relationship "{name}" '
                           +f'within {key}, but another forced relationship '
                           +f'exists in {key} with the same name.')
        _rel_set.add((key, name))

        _relationship[key].append(val)
    args.relationship = _relationship
    engine = create_engine(args.url)
    metadata = MetaData(engine)
    tables = args.tables.split(',') if args.tables else None
    metadata.reflect(engine, args.schema, not args.noviews, tables)
    outfile = codecs.open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout

    if args.audited:
        args.audited = set(args.audited.split(','))

    generator = CodeGenerator(metadata,
                              args.noindexes,
                              args.noconstraints,
                              args.nojoined,
                              args.noinflect,
                              args.noclasses,
                              audited=args.audited,
                              audit_all=args.auditall,
                              flask_login_user=args.loginuser,
                              flask_login_role=args.loginrole,
                              force_relationship=args.relationship)
    generator.render(outfile)
