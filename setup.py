# ***** BEGIN LICENSE BLOCK *****
#
# For copyright and licensing please refer to LICENSE.
#
# ***** END LICENSE BLOCK *****
from setuptools import setup

long_description = ('Ariane Plugin PROCOS map your operating process interactions and more.'
                    'Where you can get more informations : '
                    '   + http://ariane.echinopsii.net'
                    '   + http://confluence.echinopsii.net/confluence/display/AD/Ariane+Documentation+Home'
                    '   + IRC on freenode #ariane.echinopsii')

setup(name='ariane_procos',
      version='0.1.5-b01',
      description='Ariane Plugin ProcOS',
      long_description=long_description,
      author='Mathilde Ffrench',
      author_email='mathilde.ffrench@echinopsii.net',
      maintainer='Mathilde Ffrench',
      maintainer_email='mathilde.ffrench@echinopsii.net',
      url='https://github.com/echinopsii/net.echinopsii.ariane.community.plugin.procos.git',
      download_url='https://github.com/echinopsii/net.echinopsii.ariane.community.plugin.procos.git/tarball/0.1.5-b01',
      packages=['ariane_procos'],
      license='AGPLv3',
      install_requires=['netifaces>=0.10.4', 'psutil>=3.3.0,<4.0', 'pykka>=1.2.1', 'ariane_clip3==0.1.6-b01'],
      package_data={'': ['LICENSE', 'README.md']},
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU Affero General Public License v3',
          'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: Implementation :: CPython',
          'Topic :: Communications',
          'Topic :: Internet',
          'Topic :: Software Development :: Libraries',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Monitoring',
          'Topic :: System :: Networking'],
      zip_safe=True)
