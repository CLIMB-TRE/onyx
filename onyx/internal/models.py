from django.db import models
from accounts.models import User


# Credit to tuatara for this lookup
# https://gist.github.com/tuatara/6188a4c7bacab1f52c80
@models.CharField.register_lookup
@models.TextField.register_lookup
class LengthLookup(models.Transform):
    lookup_name = "length"

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return "CHAR_LENGTH(%s)" % lhs, params

    # SQLite doesn't implement CHAR_LENGTH, but its implementation of LENGTH conforms
    # with standard SQL CHAR_LENGTH (i.e. number of chars, not number of bytes)
    def as_sqlite(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return "LENGTH(%s)" % lhs, params

    @property
    def output_field(self):
        return models.IntegerField()


# Override of the default isnull lookup for CharField and TextField
# Instead of checking for NULL, checks for the empty string
@models.CharField.register_lookup
@models.TextField.register_lookup
class TextIsNull(models.Lookup):
    lookup_name = "isnull"
    prepare_rhs = False  # TODO: Needed this but I don't understand why

    def as_sql(self, compiler, connection):
        if not isinstance(self.rhs, bool):
            raise ValueError(
                "The QuerySet value for an isnull lookup must be True or False."
            )

        sql, params = self.process_lhs(compiler, connection)

        if self.rhs:
            return "%s = ''" % sql, params
        else:
            return "%s <> ''" % sql, params


class RequestHistory(models.Model):
    endpoint = models.CharField(max_length=100, blank=True)
    method = models.CharField(max_length=10, blank=True)
    status = models.PositiveSmallIntegerField()
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    address = models.CharField(max_length=20, blank=True)
    exec_time = models.IntegerField(null=True)
    date = models.DateTimeField(auto_now=True)
    error_messages = models.TextField(blank=True)
