# WeFinance Privacy Notice (Anna App)

Last updated: 2026-09-28

This notice covers the WeFinance app in the Anna App Store (`@calderbuild/wefinance`).

## What I don't do

- I run no server for this app. WeFinance has no backend of its own, and none of its code sends anything to me.
- It never asks you to link a bank account, card, or payment app.
- There are no ads, analytics, or tracking scripts in the app.

## What happens to your data

- **Bill photos.** When you scan a bill, the image goes to Anna's model service so the model can read it. The app doesn't keep the image. It keeps only the transactions the model extracted.
- **Transactions and budget.** These are saved in your own Anna app storage (`anna.storage`), under your account. Other users can't see them, and neither can I.
- **Questions and recommendation inputs.** Your question, your transactions, and any income, goal, or horizon you type are sent to Anna's model service to write the answer. None of it is sent anywhere else.
- **Deleting your data.** The "Clear all scanned transactions" button on the Scan tab deletes every stored transaction.

Anna's own handling of model requests and storage is covered by Anna's privacy policy: https://anna.partners/legal/privacy

## Not financial advice

WeFinance gives general, educational suggestions based on the numbers you give it. It is not a licensed financial advisor. Check with a qualified professional before you make investment decisions.

## Contact

Open an issue at https://github.com/calderbuild/WeFinance/issues
