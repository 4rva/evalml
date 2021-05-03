from skopt.space import Real

from evalml.model_family import ModelFamily
from evalml.pipelines.components.estimators import Estimator
from evalml.problem_types import ProblemTypes
from evalml.utils import get_logger, import_or_raise
from evalml.utils.gen_utils import make_h2o_ready

logger = get_logger(__file__)


class GAMRegressor(Estimator):
    """GAM Regressor"""
    name = "GAM Regressor"
    hyperparameter_ranges = {
        "solver": ["IRLSM", "L_BFGS"],
        "alpha": Real(0.000001, 1),
        "lambda": Real(0.000001, 1),
        "family": ["Gaussian", "Poisson", "Gamma"],
        "link": ["Identity", "Log", "Inverse"]
    }
    model_family = ModelFamily.GAM
    supported_problem_types = [ProblemTypes.REGRESSION]

    def __init__(self, family='AUTO', solver="AUTO", stopping_metric="deviance", keep_cross_validation_models=False, random_seed=0, **kwargs):

        self._parameters = {"family": family,
                            "solver": solver,
                            "stopping_metric": stopping_metric,
                            "keep_cross_validation_models": keep_cross_validation_models,
                            "seed": random_seed}
        self._parameters.update(kwargs)

        h2o_error_msg = "H2O is not installed. please install using `pip install h2o`."
        self.h2o = import_or_raise("h2o", error_msg=h2o_error_msg)

        self.h2o_model_init = self.h2o.estimators.gam.H2OGeneralizedAdditiveEstimator

        super().__init__(parameters=self._parameters,
                         component_obj=None,
                         random_state=random_seed)

    def _update_params(self, X, y):
        X_cols = [str(col_) for col_ in list(X.columns)]
        new_params = {'gam_columns': X_cols,
                      "lambda_search": True}
        new_params.update({"family": "Gaussian",
                           "link": "Identity"})
        return new_params

    def fit(self, X, y=None):
        self.h2o.init()
        if y is None:
            raise ValueError('GAM Regressor requires y as input.')
        X, y, training_frame = make_h2o_ready(X, y, supported_problem_types=GAMRegressor.supported_problem_types)
        new_params = self._update_params(X, y)
        self._parameters.update(new_params)
        self.h2o_model = self.h2o_model_init(**self._parameters)
        self.h2o_model.train(x=list(X.columns), y=y.name, training_frame=training_frame)
        return self.h2o_model

    def predict(self, X):
        X = make_h2o_ready(X, supported_problem_types=GAMRegressor.supported_problem_types)
        X = self.h2o.H2OFrame(X)
        predictions = self.h2o_model.predict(X)
        predictions = predictions.as_data_frame(use_pandas=True).iloc[:, 0]
        return predictions

    @property
    def feature_importance(self):
        return self.h2o_model.varimp()
