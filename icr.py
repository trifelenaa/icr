# -*- coding: utf-8 -*-
"""icr

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1LX9VHJb2pJ3XqcG6AoziF9U8jydvPYiH

# Загрузка данных и библиотек

Загрузить данные можно отсюда: [*диск*](https://disk.yandex.ru/d/e__jZ9teH51-7Q)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.model_selection import KFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import KNNImputer
from sklearn.model_selection import GridSearchCV
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import roc_auc_score
from sklearn.metrics import accuracy_score

# загружаем тренировочные и тестовые данные
train_data = pd.read_csv('train.csv')
test_data = pd.read_csv('test.csv')

# выводим первые пять строк
train_data.head()

"""# Препроцессинг и балансировка классов"""

# информация о датасете тренировочном
train_data.info()

# построим диаграмму соотношений целевого класса, видим, что он не сбалансирован
plot_df = train_data.Class.value_counts()
plot_df.plot(kind="pie")

# посчитаем количество 1 и 0 в целевом классе
neg, pos = np.bincount(train_data['Class'])
# соотношение
total = neg + pos
print('Examples:\n    Total: {}\n    Positive: {} ({:.2f}% of total)\n'.format(
    total, pos, 100 * pos / total))

# рассчитаем вес каждого класса, чтобы учитывать это при обучении
weight_for_0 = (1 / neg) * (total / 2.0)
weight_for_1 = (1 / pos) * (total / 2.0)

class_weight = {0: weight_for_0, 1: weight_for_1}

print('Weight for class 0: {:.2f}'.format(weight_for_0))
print('Weight for class 1: {:.2f}'.format(weight_for_1))

sample_weight = compute_sample_weight(class_weight=class_weight, y=train_data['Class'])

#sample_weight.shape

#немного преобразуем данные: заполним пропуски, превратим категориальные данные в количественные
X = train_data.drop(columns = ['Id', 'Class'],axis=1)
X_test = test_data.drop(columns = ['Id'],axis=1)

categorical_columns = X.select_dtypes(include=['object']).columns
X = pd.get_dummies(X, columns=categorical_columns, drop_first=True)
X_test = pd.get_dummies(X_test, columns=categorical_columns, drop_first=True)

X, X_test = X.align(X_test, join='outer', axis=1, fill_value=0)

imputer = KNNImputer(n_neighbors=5)
X = pd.DataFrame(imputer.fit_transform(X), columns=X.columns)
X_test = pd.DataFrame(imputer.fit_transform(X_test), columns=X_test.columns)

y = train_data['Class']

"""# Обучение с использованием кросс-валидации (KFold)"""

# создаем пять фолдов
kf = KFold(n_splits=5)

# здесь будем хранить модели для каждого фолда
models = {}

# лосс-функция
def balanced_log_loss(y_true, y_pred):

    N_0 = np.sum(1 - y_true)
    N_1 = np.sum(y_true)
    w_0 = 1 / N_0
    w_1 = 1 / N_1
    p_1 = np.clip(y_pred, 1e-15, 1 - 1e-15)
    p_0 = 1 - p_1

    log_loss_0 = -np.sum((1 - y_true) * np.log(p_0))
    log_loss_1 = -np.sum(y_true * np.log(p_1))
    balanced_log_loss = 2*(w_0 * log_loss_0 + w_1 * log_loss_1) / (w_0 + w_1)

    return balanced_log_loss/(N_0+N_1)

# само обучение и кросс-валидация, кроме того проведем визуализацию
accuracy_scores ={}
test_losses = {}

figure, axis = plt.subplots(3, 2, figsize=(10, 10))
plt.subplots_adjust(hspace=0.5, wspace=0.3)

for i, (train_index, val_index) in enumerate(kf.split(X, y=y)):

    row = i//2
    col = i % 2

    X_train, X_val = X.iloc[train_index], X.iloc[val_index]
    y_train, y_val = y.iloc[train_index], y.iloc[val_index]

    test_loss = []
    accuracy = []

    # рассмотрим разное количество деревьев (от одного до 300, но с разным промежутком, т.к. в какой-то момент изменения становятся почти незаметными)
    list_nb_trees = list(range(1, 26))
    list_nb_trees.extend(range(25, 301, 25))

    for nb_trees in list_nb_trees:

      model = RandomForestClassifier(n_estimators=nb_trees,max_depth=30,random_state=42)
      model.fit(X_train, y_train, sample_weight=sample_weight[train_index])
      test_loss.append(balanced_log_loss(y_val, model.predict_proba(X_val)[:,1]))
      #test_loss.append(roc_auc_score(y_val, model.predict_proba(X_val)[:,1]))
      accuracy.append(accuracy_score(y_val, model.predict(X_val)))

    # график функции потерь при различном кодичестве деревьев на каждом фолде
    axis[row, col].plot(list_nb_trees, test_loss, color="g", label="Testing Score")
    axis[row, col].set_title(f"Fold {i+1}")
    axis[row, col].set_xlabel('Number of trees')
    axis[row, col].set_ylabel('Balanced Log Loss)')

    models[f'fold_{i+1}'] = model
    test_losses[f'fold_{i+1}'] = test_loss
    accuracy_scores[f'fold_{i+1}'] = accuracy

axis[2][1].set_visible(False)
plt.show()

"""# Выбор лучшей модели и предсказания"""

# считаем лосс и точность для каждого фолда
average_loss = 0
average_acc = 0

for _model in  models:
    average_loss += test_losses[_model][36]
    average_acc += accuracy_scores[_model][36]
    print(f"{_model}: acc: { accuracy_scores[_model][36]:.4f} loss: {test_losses[_model][36]:.4f}")

print(f"\nAverage accuracy: {average_acc/5:.4f}  Average loss: {average_loss/5:.4f}")

# при помощи выбранного осуществляем предсказания
predictions = models['fold_1'].predict_proba(X_test)
predictions

# запись в файл
sample_submission = pd.read_csv("sample_submission.csv")
sample_submission[['class_0', 'class_1']] = predictions
sample_submission.to_csv('submission.csv', index=False)