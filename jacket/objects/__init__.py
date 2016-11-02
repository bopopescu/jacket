#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# NOTE(nkapotoxin): All jacket objects are registered, an attribute is set
# on this module automatically, pointing to the newest/latest version of
# the object.

from jacket.objects import compute
from jacket.objects import extend
from jacket.objects import storage


def register_all():
    compute.register_all()
    storage.register_all()
    extend.register_all()
