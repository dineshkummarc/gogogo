import uuid
import os

import dulwich.errors
from dulwich.repo import Repo
from dulwich.objects import Tree, Blob

from gogogo import BoardState

DEFAULTS = dict(
    black="Black",
    white="White",
    x=19,
    y=19,
    data=os.path.join('.', 'data', '{name}'),
    create=False
)

class GameError(Exception): pass

class Game(object):
    "A versioned game"
    def __init__(self, name=None, **options):
        self.name = name or uuid.uuid4().hex
        self.options = dict(DEFAULTS, **options)
        self.data = self.options.pop('data').format(name=self.name)
        new = False

        self.repo = None
        if not os.path.exists(self.data):
            if not self.options['create']: raise GameError("Game does not exist")
            os.makedirs(self.data)

        try:
            self.repo = Repo(self.data)
        except dulwich.errors.NotGitRepository:
            if not self.options['create']: raise GameError("Game does not exist")
            self.repo = Repo.init_bare(self.data)
            new = True


        self.board = (new and BoardState()) or self.get_board()

        if new: self.save("New blank board for game: %s" % self.name)

    @property
    def branch(self):
        head = self.repo.refs.read_ref('HEAD')
        if head and head.startswith('ref: '):
            head = head.split(': ')[-1]
            head = head.replace('refs/heads/', '')
            return head
        return 'master'

    def _tree(self, branch=None):
        branch = branch or self.branch
        try: return self.repo[
                      self.repo['refs/heads/%s' % branch].tree
                    ]
        except KeyError: return Tree()

    def signature(self, of=None):
        of = (of and "refs/heads/%s" % of) or "HEAD"
        try: return self.repo.refs[of]
        except KeyError: return None


    def get_board(self, branch=None):
        branch = branch or self.branch
        if branch not in self.branches(): raise GameError("Unknown branch")
        return BoardState.from_json(
            self.repo[
                  [t[2] 
                   for t in self._tree(branch).entries() # [(mode, name, sha)...]
                   if t[1] == 'board.json'].pop()
                 ].data)

    def set_branch(self, new):
        if 'refs/heads/%s' % new in self.repo.get_refs().keys():
            self.repo.refs.set_symbolic_ref('HEAD', 'refs/heads/%s' % new)
            return self.branch
        return False

    def branches(self):
        return sorted([name.replace('refs/heads/', '')
                       for (name, sig) in self.repo.get_refs().items()
                       if name != "HEAD"])

    def make_branch(self, name, back=0):
        if ('refs/heads/%s' % name) in self.repo.get_refs().keys():
            raise GameError("I already have this branch")
        try:
            head = self.repo.head()
            history = self.repo.revision_history(head)
            self.repo.refs['refs/heads/%s' % name] = history[back].id
        except IndexError:
            raise GameError("Trying to go {back} which is further than history".format(back=back))
        return True


    def save(self, message="Forced commit"):
        blob = Blob.from_string(self.board.as_json())
        tree = self._tree()
        tree.add(0100644, 'board.json', blob.id)

        [self.repo.object_store.add_object(it)
         for it in (blob, tree)]

        self.repo.do_commit(message, committer="Game %s" % self.name, tree=tree.id)

    def move(self, x, y):
        player = self.board.player_turn()
        if not self.board.game_over and self.board.move(x, y):
            self.save("{player} moved to ({x}, {y})".format(player=player,
                                                            x=x,
                                                            y=y))
            return player
        return None

    def skip(self):
        player = self.board.player_turn()
        if not self.board.game_over:
            self.board.move(None)
            is_or_isnt = (self.board.game_over and "is") or "is NOT"
            self.save("{player} skipped, game {maybe} over".format(player=player,
                                                                   maybe=is_or_isnt))
        return self.board.game_over or self.board.player_turn()

    def who(self):
        return self.board.player_turn()

    def scores(self):
        return self.board.scores()

    def winner(self):
        return self.board.winner

    def __unicode__(self):
        return "Game: {name} {black} vs {white} on {x}x{y} from {data} :: {board}".format(
                 name=self.name,
                 board=self.board,
                 data=self.data,
                 **self.options
               )
    __str__=__unicode__

    def __repr__(self):
        return "<%s>" % self
