# NPС Rates - Сервис управления курсами валют с сайта [НБ РБ](https://www.nbrb.by/)

![Image alt](https://img.shields.io/badge/python-%203.10-blue)

Проект выполнен в рамках технического задания. Описание <a href='technical_task'> здесь</a>.

### Подробнее об эндпойнтах:
****
**rates/import_rates/ (http://127.0.0.1:8000/rates/import_rates/) - для загрузки курсов в систему. Это POST запрос, параметрами передается json словарь вида {'date_import': '2023-03-30'}**

**rates/get_rate/YYYY-MM-DD/CUR_CODE - Получение данных о курсах валют из НЦ РБ по указанной дате (http://127.0.0.1:8000/rates/get_rate/2023-03-30/USD/)**


## Чтобы развернуть проект локально:

### Клонируйте данный репозиторий и перейдите с директорию с проектом
```
git clone https://github.com/wezbicka/npc-rates.git
cd npc-rates
 ```
### Создайте и активируйте виртуальное окружение
```
python -m venv venv
source ./venv/Scripts/activate  #для Windows
source ./venv/bin/activate      #для Linux и macOS
```
### Установите требуемые зависимости
```
pip install -r requirements.txt
```
### Запустите проект
```
python manage.py runserver
```
#### Приложение будет доступно по адресу: http://127.0.0.1:8000/

****
**1. Наполнить базу данных курсами валют вызвав endpoint - rates/import_rates/**

**2. Получить данные о курсах валют вызвав endpoint - rates/get_rate/2023-03-30/USD/**
