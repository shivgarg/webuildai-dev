class FeaturesController < ApplicationController
 before_action :set_feature, only: [:show, :edit, :update, :destroy]

  # GET /features
  # GET /features.json
  def index
    @features = Feature.all
  end

  # GET /features/1
  # GET /features/1.json
  def show
  end

  # GET /features/new
  def new
    @feature = Feature.new
  end

  # GET /features/1/edit
  def edit
  end

  # POST /features
  # POST /features.json
  def create
   name = params[:name]
   cat = params[:cat]
   #continuous feature creation code
   if cat.to_i == 0
     lower = params[:lower]
     upper = params[:upper]
     if Feature.where(name: name).empty?
       a = Feature.create(name: name)
       a.description = params[:description]
       a.description = "Your Own Feature(s) - Continuous" if params[:description].blank?
       a.active = true
       a.category = params[:category]
       a.save!
       DataRange.create(feature_id: a.id, is_categorical: false, lower_bound: lower.to_i, upper_bound: upper.to_i)
     else
      a = Feature.where(name: name).first
      a.description = params[:description]
      a.description = "Your Own Feature(s) - Continuous" if params[:description].blank?
      a.active = true
      a.category = params[:category]
      a.save!
      d = a.data_range
      if !d.nil?
        if !d.categorical_data_options.empty?
          d.categorical_data_options.each do |dao|
            dao.destroy!
          end
        end
        d.lower_bound = lower.to_i
        d.upper_bound = upper.to_i
        d.is_categorical = false
        d.save!
      else
         DataRange.create(feature_id: a.id, is_categorical: false, lower_bound: lower.to_i, upper_bound: upper.to_i)
      end
     end
   else
     opts =  (params[:opts]).split("*")
     if Feature.where(name: name).empty?
       a = Feature.create(name: name)
       a.category = params[:category]
       a.description = params[:description]
       a.description = "Your Own Feature(s) - Categorical" if params[:description].blank?
       a.active = true
       a.save!
       rng = DataRange.create(feature_id: a.id, is_categorical: true, lower_bound: nil, upper_bound: nil)
       (params[:opts]).split("*").each do |o|
         CategoricalDataOption.create(data_range_id: rng.id, option_value: o)
       end
     else
      a = Feature.where(name: name).first
      a.description = params[:description]
      a.description = "Your Own Feature(s) - Categorical" if params[:description].blank?
      a.active = true
      a.category = params[:category]
      a.save!
      d = a.data_range
      if !d.nil?
        if !d.categorical_data_options.empty?
          d.categorical_data_options.each do |dao|
            dao.destroy!
          end
        end
        d.lower_bound = nil
        d.upper_bound = nil
        d.is_categorical = true
        d.save!
      else
        d = DataRange.create(feature_id: a.id, is_categorical: true, lower_bound: nil, upper_bound: nil)
      end

      (params[:opts]).split("*").each do |o|
        CategoricalDataOption.create(data_range_id: d.id, option_value: o)
      end

     end
   end

  end

  # PATCH/PUT /features/1
  # PATCH/PUT /features/1.json
  def update
   @feature.active = false
   @feature.save!
  end


  # DELETE /features/1
  # DELETE /features/1.json
  def destroy
    @feature.destroy
    respond_to do |format|
      format.html { redirect_to features_url, notice: 'Feature was successfully destroyed.' }
      format.json { head :no_content }
    end
  end

  private
    # Use callbacks to share common setup or constraints between actions.
    def set_feature
      @feature = Feature.find(params[:id])
    end

    # Never trust parameters from the scary internet, only allow the white list through.
    def feature_params
      params.require(:feature).permit(:name, :cat, :lower, :upper, :opts, :category, :description)
    end
end
