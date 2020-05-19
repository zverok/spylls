import jamspell

corrector = jamspell.TSpellCorrector()
corrector.LoadLangModel('en.bin')

corrector.FixFragment('Wich wya is mcDonalds')
