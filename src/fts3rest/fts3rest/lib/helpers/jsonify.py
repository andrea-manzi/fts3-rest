#   Copyright notice:
#   Copyright  Members of the EMI Collaboration, 2013.
#
#   See www.eu-emi.eu for details on the copyright holders
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

from datetime import datetime
from decorator import decorator
from fts3.model.base import Base
from pylons.decorators.util import get_pylons
import json


class ClassEncoder(json.JSONEncoder):

    def __init__(self, *args, **kwargs):
        super(ClassEncoder, self).__init__(*args, **kwargs)
        self.visited = []

    def default(self, obj):
        if isinstance(obj, Base):
            self.visited.append(obj)

        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%S%z')
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, Base) or isinstance(obj, object):
            str(obj) # Trigger sqlalchemy if needed
            values = {}
            for (k, v) in obj.__dict__.iteritems():
                if not k.startswith('_') and v not in self.visited:
                    values[k] = v
                    if isinstance(v, Base):
                        self.visited.append(v)
            return values
        else:
            return super(ClassEncoder, self).default(obj)


def to_json(data):
    return [json.dumps(data, cls=ClassEncoder, indent=2, sort_keys=True)]


@decorator
def jsonify(f, *args, **kwargs):
    """
    Decorates methods in the controllers, and converts the output to a JSON
    serialization

    Args:
        f:      The method to be called
        args:   Parameters for f
        kwargs: Named parameters for f

    Returns:
        A string with the JSON representation of the value returned by f()
    """
    pylons = get_pylons(args)
    pylons.response.headers['Content-Type'] = 'application/json'

    data = f(*args, **kwargs)
    return [json.dumps(data, cls=ClassEncoder, indent=2, sort_keys=True)]
