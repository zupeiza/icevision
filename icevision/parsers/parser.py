__all__ = ["ParserInterface", "Parser"]

from icevision.imports import *
from icevision.utils import *
from icevision.core import *
from icevision.data import *
from icevision.parsers.mixins import *


# TODO: Rename to BaseParser
class ParserInterface(ABC):
    @abstractmethod
    def parse(
        self, data_splitter: DataSplitter, autofix: bool = True, show_pbar: bool = True
    ) -> List[List[RecordType]]:
        pass


class Parser(ImageidMixin, ParserInterface, ABC):
    """Base class for all parsers, implements the main parsing logic.

    The actual fields to be parsed are defined by the mixins used when
    defining a custom parser. The only required field for all parsers
    is the `image_id`.

    # Examples

    Create a parser for image filepaths.
    ```python
    class FilepathParser(Parser, FilepathParserMixin):
        # implement required abstract methods
    ```
    """

    @abstractmethod
    def __iter__(self) -> Any:
        pass

    def prepare(self, o):
        pass

    def record_class(self) -> BaseRecord:
        record_bases = self.record_mixins()
        return type("Record", (BaseRecord, *record_bases), {})

    def parse_dicted(
        self, idmap: IDMap, show_pbar: bool = True
    ) -> Dict[int, RecordType]:

        Record = self.record_class()
        records = defaultdict(Record)

        for sample in pbar(self, show_pbar):
            self.prepare(sample)

            imageid = idmap[self.imageid(sample)]
            record = records[imageid]

            self.parse_fields(sample, record)
            # HACK: fix imageid (needs to be transformed with idmap)
            record.set_imageid(imageid)

        # check that all annotations have the same length
        # HACK: Masks is not checked, because it can be a single file with multiple masks
        # annotations_names = [n for n in annotation_parse_funcs.keys() if n != "masks"]
        # for imageid, record_annotations in records.items():
        #     record_annotations_len = {
        #         name: len(record_annotations[name]) for name in annotations_names
        #     }
        #     if not allequal(list(record_annotations_len.values())):
        #         true_imageid = idmap.get_id(imageid)
        #         # TODO: instead of immediatily raising the error, store the
        #         # result and raise at the end of the for loop for all records
        #         raise RuntimeError(
        #             f"imageid->{true_imageid} has an inconsistent number of annotations"
        #             f", all annotations must have the same length."
        #             f"\nNumber of annotations: {record_annotations_len}"
        #         )

        return dict(records)

    def parse(
        self,
        data_splitter: DataSplitter = None,
        idmap: IDMap = None,
        autofix: bool = True,
        show_pbar: bool = True,
    ) -> List[List[BaseRecord]]:
        """Loops through all data points parsing the required fields.

        # Arguments
            data_splitter: How to split the parsed data, defaults to a [0.8, 0.2] random split.
            idmap: Maps from filenames to unique ids, pass an `IDMap()` if you need this information.
            show_pbar: Whether or not to show a progress bar while parsing the data.

        # Returns
            A list of records for each split defined by `data_splitter`.
        """
        idmap = idmap or IDMap()
        data_splitter = data_splitter or RandomSplitter([0.8, 0.2])
        records = self.parse_dicted(show_pbar=show_pbar, idmap=idmap)

        splits = data_splitter(idmap=idmap)
        all_splits_records = []
        for ids in splits:
            split_records = [records[i] for i in ids]

            if autofix:
                split_records = autofix_records(split_records)

            all_splits_records.append(split_records)

        return all_splits_records

    @classmethod
    def _templates(cls) -> List[str]:
        templates = super()._templates()
        return ["def __iter__(self) -> Any:"] + templates

    @classmethod
    def generate_template(cls):
        for template in cls._templates():
            print(f"{template}")
