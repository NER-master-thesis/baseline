import itertools
import numpy as np
import matplotlib.pyplot as plt

def plot_confusion_matrix(cm, classes):
    """
    This function prints and plots the confusion matrix.
    
	@type cm: numpy array
	@param cm: confusion matrix
	@type classes: list
	@param classes: list of the class labels
    """

    title='Confusion matrix' 
    cmap=plt.cm.Blues

    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, cm[i, j], horizontalalignment="center", color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.show()
