#   Copyright notice:
#   Copyright  CERN, 2014.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

try:
    import json
except:
    import simplejson as json

from base import Base
from fts3.rest.client import Inquirer


def _human_readable_snapshot(logger, snapshot):
    for entry in snapshot:
        logger.info("Source:               %s" % entry.get('source_se'))
        logger.info("Destination:          %s" % entry.get('dest_se'))
        logger.info("VO:                   %s" % entry.get('vo_name'))
        logger.info("Max. Active:          %d" % entry.get('max_active', 0))
        logger.info("Active:               %d" % entry.get('active', 0))
        logger.info("Submitted:            %d" % entry.get('submitted', 0))
        logger.info("Finished:             %d" % entry.get('finished', 0))
        logger.info("Failed:               %d" % entry.get('failed', 0))
        ratio = entry.get('success_ratio', None)
        if ratio:
            logger.info("Success ratio:        %.2f%%" % ratio)
        else:
            logger.info("Success ratio:       -")
        avg_thr = entry.get('avg_throughput', None)
        if isinstance(avg_thr, float):
            logger.info("Avg. Throughput:      %.2f MB/s" % avg_thr)
        elif isinstance(avg_thr, dict):
            for interval, thr in sorted(avg_thr.iteritems(), key=lambda p: int(p[0])):
                if thr is not None:
                    logger.info("Avg. Throughput (%2d): %.2f MB/s" % (int(interval), thr))
                else:
                    logger.info("Avg. Throughput (%2d): -" % int(interval))
        else:
            logger.info("Avg. Throughput:      -")

        avg_queued = entry.get('avg_queued')
        if avg_queued is not None:
            logger.info("Avg. Queued:          %d seconds" % avg_queued)
        else:
            logger.info("Avg. Queued:          -")
        frequent_error = entry.get('frequent_error', None)
        if frequent_error and 'count' in frequent_error and 'reason' in frequent_error:
            logger.info("Most frequent error:  [%d] %s" % (frequent_error['count'], frequent_error['reason']))
        else:
            logger.info("Most frequent error:  -")
        limits = entry.get('limits', None)
        if isinstance(limits, dict):
            if limits.get('source', None):
                logger.info("Max. Source Thr:      %.2f" % limits['source'])
            if limits.get('destination', None):
                logger.info("Max. Dest. Thr:       %.2f" % limits['destination'])
        logger.info("\n")


class Snapshot(Base):
    def __init__(self):
        super(Snapshot, self).__init__(
            description="""
            This command can be used to retrieve the internal status FTS3 has on all pairs with ACTIVE transfers.
            It allows to filter by VO, source SE and destination SE
            """,
            example="""
            $ %(prog)s -s https://fts3-devel.cern.ch:8446
            Source:              gsiftp://whatever
            Destination:         gsiftp://whatnot
            VO:                  dteam
            Max. Active:         5
            Active:              1
            Submitted:           0
            Finished:            0
            Failed:              0
            Success ratio:       -
            Avg. Throughput:     -
            Avg. Duration:       -
            Avg. Queued:         0 seconds
            Most frequent error: -
            """
        )
        # Specific options
        self.opt_parser.add_option('--vo', dest='vo',
                                   help='filter by VO')
        self.opt_parser.add_option('--source', dest='source',
                                   help='filter by source SE')
        self.opt_parser.add_option('--destination', dest='destination',
                                   help='filter by destination SE')

    def run(self):
        context = self._create_context()
        inquirer = Inquirer(context)
        snapshot = inquirer.get_snapshot(self.options.vo, self.options.source, self.options.destination)
        if self.options.json:
            self.logger.info(json.dumps(snapshot, indent=2))
        else:
            _human_readable_snapshot(self.logger, snapshot)
