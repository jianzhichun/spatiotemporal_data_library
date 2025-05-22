Examples
========

Basic Usage
----------

.. code-block:: python

    from spatiotemporal_data_library import SpatiotemporalData
    
    # Create a new instance
    data = SpatiotemporalData()
    
    # Load data
    data.load_from_csv('data.csv')
    
    # Process data
    processed_data = data.process()
    
    # Save results
    processed_data.save_to_csv('results.csv')

Advanced Usage
------------

.. code-block:: python

    from spatiotemporal_data_library import SpatiotemporalData
    
    # Create instance with custom parameters
    data = SpatiotemporalData(
        time_column='timestamp',
        location_column='coordinates',
        value_column='measurement'
    )
    
    # Apply custom processing
    data.apply_custom_processing(
        method='interpolation',
        parameters={'method': 'cubic'}
    ) 