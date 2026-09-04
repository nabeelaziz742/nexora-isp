from django.contrib import admin
from .models import (
    Account,
    FinancialPeriod,
    JournalEntry,
    JournalLine,
    Expense,
    DirectIncome,
    FundTransfer,
    DealerSettlement,
)

admin.site.register(Account)
admin.site.register(FinancialPeriod)
admin.site.register(JournalEntry)
admin.site.register(JournalLine)
admin.site.register(Expense)
admin.site.register(DirectIncome)
admin.site.register(FundTransfer)
admin.site.register(DealerSettlement)
